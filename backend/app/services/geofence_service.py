from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Device, Geofence, GeofenceEvent, GeofenceEventType, LocationEvent
from app.schemas.platform import GeofenceCreateRequest, GeofenceUpdateRequest


class GeofenceService:
    async def create_geofence(self, session: AsyncSession, payload: GeofenceCreateRequest) -> Geofence:
        if payload.device_id is not None:
            device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
            if device is None:
                raise ValueError('Unknown device_id')
            if device.organization_id != payload.org_id:
                raise ValueError('Device does not belong to tenant org.')

        geofence = Geofence(
            org_id=payload.org_id,
            device_id=payload.device_id,
            name=payload.name,
            radius_meters=payload.radius_meters,
            center_latitude=payload.center_latitude,
            center_longitude=payload.center_longitude,
            center_geom=func.ST_SetSRID(func.ST_MakePoint(payload.center_longitude, payload.center_latitude), 4326),
            is_enabled=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(geofence)
        await session.flush()
        await session.refresh(geofence)
        return geofence

    async def list_geofences(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID | None = None,
    ) -> list[Geofence]:
        stmt = select(Geofence).where(Geofence.org_id == org_id).order_by(Geofence.created_at.desc())
        if device_id is not None:
            stmt = stmt.where(Geofence.device_id == device_id)
        return list((await session.execute(stmt)).scalars().all())

    async def update_geofence(
        self,
        session: AsyncSession,
        *,
        geofence_id: UUID,
        payload: GeofenceUpdateRequest,
    ) -> Geofence:
        geofence = await self._get_geofence(session, geofence_id)
        if geofence.org_id != payload.org_id:
            raise ValueError('Geofence does not belong to tenant org.')
        if payload.device_id is not None:
            device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
            if device is None:
                raise ValueError('Unknown device_id')
            if device.organization_id != payload.org_id:
                raise ValueError('Device does not belong to tenant org.')
        geofence.device_id = payload.device_id
        geofence.name = payload.name
        geofence.radius_meters = payload.radius_meters
        geofence.center_latitude = payload.center_latitude
        geofence.center_longitude = payload.center_longitude
        geofence.center_geom = func.ST_SetSRID(func.ST_MakePoint(payload.center_longitude, payload.center_latitude), 4326)
        geofence.is_enabled = payload.is_enabled
        await session.flush()
        await session.refresh(geofence)
        return geofence

    async def delete_geofence(
        self,
        session: AsyncSession,
        *,
        geofence_id: UUID,
        org_id: UUID,
    ) -> Geofence:
        geofence = await self._get_geofence(session, geofence_id)
        if geofence.org_id != org_id:
            raise ValueError('Geofence does not belong to tenant org.')
        await session.delete(geofence)
        await session.flush()
        return geofence

    async def process_location_event(
        self,
        session: AsyncSession,
        *,
        location_event: LocationEvent,
    ) -> list[GeofenceEvent]:
        if location_event.latitude is None or location_event.longitude is None:
            return []

        previous_inside = await self._previous_inside_geofence_ids(
            session,
            org_id=location_event.org_id,
            device_id=location_event.device_id,
        )
        current_inside_rows = await self._current_inside_geofences(
            session,
            org_id=location_event.org_id,
            device_id=location_event.device_id,
            latitude=float(location_event.latitude),
            longitude=float(location_event.longitude),
        )
        current_inside = {row['geofence_id']: row['name'] for row in current_inside_rows}
        enters, exits = self.build_transition_actions(previous_inside, set(current_inside.keys()))
        if not enters and not exits:
            return []

        geofence_lookup = {row['geofence_id']: row['name'] for row in current_inside_rows}
        if exits:
            exit_rows = await session.execute(
                select(Geofence.id, Geofence.name).where(Geofence.id.in_(list(exits)))
            )
            geofence_lookup.update({row[0]: row[1] for row in exit_rows.all()})

        now = datetime.now(timezone.utc)
        events: list[GeofenceEvent] = []
        for geofence_id, event_type in [
            *[(geofence_id, GeofenceEventType.ENTER) for geofence_id in sorted(enters)],
            *[(geofence_id, GeofenceEventType.EXIT) for geofence_id in sorted(exits)],
        ]:
            emit_alert = await self.should_emit_alert(
                session,
                geofence_id=geofence_id,
                device_id=location_event.device_id,
                now=now,
            )
            event = GeofenceEvent(
                org_id=location_event.org_id,
                geofence_id=geofence_id,
                device_id=location_event.device_id,
                location_event_id=location_event.id,
                event_type=event_type,
                precision=location_event.precision,
                confidence_score=location_event.confidence_score,
                latitude=location_event.latitude,
                longitude=location_event.longitude,
                alert_emitted=emit_alert,
                suppressed_reason=None if emit_alert else 'rate_limited',
                triggered_at=location_event.captured_at,
                created_at=now,
            )
            session.add(event)
            events.append(event)
        await session.flush()
        return events

    async def should_emit_alert(
        self,
        session: AsyncSession,
        *,
        geofence_id: UUID,
        device_id: UUID,
        now: datetime,
    ) -> bool:
        last_emitted_stmt = (
            select(GeofenceEvent)
            .where(
                GeofenceEvent.geofence_id == geofence_id,
                GeofenceEvent.device_id == device_id,
                GeofenceEvent.alert_emitted.is_(True),
            )
            .order_by(GeofenceEvent.triggered_at.desc())
            .limit(1)
        )
        last_emitted = (await session.execute(last_emitted_stmt)).scalar_one_or_none()
        if last_emitted is None:
            return True
        age_seconds = (now - last_emitted.triggered_at).total_seconds()
        return age_seconds >= settings.geofence_alert_cooldown_seconds

    def build_transition_actions(
        self,
        previous_inside: set[UUID],
        current_inside: set[UUID],
    ) -> tuple[set[UUID], set[UUID]]:
        enters = current_inside - previous_inside
        exits = previous_inside - current_inside
        return enters, exits

    async def _get_geofence(self, session: AsyncSession, geofence_id: UUID) -> Geofence:
        geofence = (await session.execute(select(Geofence).where(Geofence.id == geofence_id))).scalar_one_or_none()
        if geofence is None:
            raise ValueError('Unknown geofence_id')
        return geofence

    async def _current_inside_geofences(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        latitude: float,
        longitude: float,
    ) -> list[dict]:
        result = await session.execute(
            text(
                """
                SELECT id AS geofence_id, name
                FROM geofences
                WHERE org_id = :org_id
                  AND is_enabled = TRUE
                  AND (device_id IS NULL OR device_id = :device_id)
                  AND ST_DWithin(
                        center_geom::geography,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        radius_meters
                  )
                """
            ),
            {
                'org_id': org_id,
                'device_id': device_id,
                'longitude': longitude,
                'latitude': latitude,
            },
        )
        return [dict(row._mapping) for row in result]

    async def _previous_inside_geofence_ids(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
    ) -> set[UUID]:
        result = await session.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (geofence_id) geofence_id, event_type
                    FROM geofence_events
                    WHERE org_id = :org_id
                      AND device_id = :device_id
                    ORDER BY geofence_id, triggered_at DESC
                )
                SELECT geofence_id
                FROM latest
                WHERE event_type = 'enter'
                """
            ),
            {
                'org_id': org_id,
                'device_id': device_id,
            },
        )
        return {row[0] for row in result.all()}
