from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Geofence, GeofenceEvent, Incident, LocationEvent, LocationPrecision


@dataclass(frozen=True)
class NormalizedTimeWindow:
    starts_at: datetime
    ends_at: datetime


class SpatialService:
    def normalize_window(
        self,
        *,
        starts_at: datetime | None,
        ends_at: datetime | None,
        now: datetime | None = None,
    ) -> NormalizedTimeWindow:
        current = now or datetime.now(timezone.utc)
        end = ends_at or current
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        start = starts_at or (end - timedelta(hours=settings.spatial_default_history_hours))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start > end:
            raise ValueError('starts_at must be earlier than ends_at')
        max_duration = timedelta(hours=settings.spatial_max_history_hours)
        if end - start > max_duration:
            start = end - max_duration
        return NormalizedTimeWindow(starts_at=start, ends_at=end)

    def meters_to_degrees(self, meters: int) -> float:
        return max(meters, 100) / 111_320.0

    async def get_last_known_location(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
    ) -> LocationEvent | None:
        stmt = (
            select(LocationEvent)
            .where(LocationEvent.org_id == org_id, LocationEvent.device_id == device_id)
            .order_by(LocationEvent.captured_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_location_history(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        starts_at: datetime | None,
        ends_at: datetime | None,
        limit: int = 500,
    ) -> list[LocationEvent]:
        window = self.normalize_window(starts_at=starts_at, ends_at=ends_at)
        stmt = (
            select(LocationEvent)
            .where(
                LocationEvent.org_id == org_id,
                LocationEvent.device_id == device_id,
                LocationEvent.captured_at >= window.starts_at,
                LocationEvent.captured_at <= window.ends_at,
            )
            .order_by(LocationEvent.captured_at.asc())
            .limit(limit)
        )
        return list((await session.execute(stmt)).scalars().all())

    async def get_geofence_events(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        device_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        limit: int = 500,
    ) -> list[tuple[GeofenceEvent, str | None]]:
        stmt = (
            select(GeofenceEvent, Geofence.name)
            .join(Geofence, Geofence.id == GeofenceEvent.geofence_id)
            .where(
                GeofenceEvent.org_id == org_id,
                GeofenceEvent.device_id == device_id,
                GeofenceEvent.triggered_at >= starts_at,
                GeofenceEvent.triggered_at <= ends_at,
            )
            .order_by(GeofenceEvent.triggered_at.asc())
            .limit(limit)
        )
        return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]

    async def get_incident_route(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        incident_id: UUID,
        starts_at: datetime | None,
        ends_at: datetime | None,
        limit: int = 500,
    ) -> tuple[Incident, list[LocationEvent], list[tuple[GeofenceEvent, str | None]], NormalizedTimeWindow]:
        incident = (
            await session.execute(select(Incident).where(Incident.id == incident_id, Incident.org_id == org_id))
        ).scalar_one_or_none()
        if incident is None:
            raise ValueError('Unknown incident_id')
        base_window = self.normalize_window(starts_at=starts_at or incident.created_at, ends_at=ends_at or incident.updated_at)
        points = await self.get_location_history(
            session,
            org_id=org_id,
            device_id=incident.device_id,
            starts_at=base_window.starts_at,
            ends_at=base_window.ends_at,
            limit=limit,
        )
        geofence_events = await self.get_geofence_events(
            session,
            org_id=org_id,
            device_id=incident.device_id,
            starts_at=base_window.starts_at,
            ends_at=base_window.ends_at,
            limit=limit,
        )
        return incident, points, geofence_events, base_window

    async def get_device_clusters(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        starts_at: datetime | None,
        ends_at: datetime | None,
        cell_size_meters: int = 10_000,
    ) -> list[dict]:
        window = self.normalize_window(starts_at=starts_at, ends_at=ends_at)
        cell_size_degrees = self.meters_to_degrees(cell_size_meters)
        result = await session.execute(
            text(
                """
                WITH latest AS (
                    SELECT DISTINCT ON (device_id)
                        device_id,
                        captured_at,
                        precision::text AS precision,
                        is_ip_approximate,
                        ST_SnapToGrid(location_geom, :cell_size_degrees, :cell_size_degrees) AS cell_geom
                    FROM location_events
                    WHERE org_id = :org_id
                      AND location_geom IS NOT NULL
                      AND captured_at >= :starts_at
                      AND captured_at <= :ends_at
                    ORDER BY device_id, captured_at DESC
                )
                SELECT
                    md5(ST_AsText(cell_geom)) AS cluster_id,
                    ST_Y(ST_Centroid(cell_geom)) AS center_latitude,
                    ST_X(ST_Centroid(cell_geom)) AS center_longitude,
                    COUNT(*) AS device_count,
                    SUM(CASE WHEN precision = 'approximate' OR is_ip_approximate THEN 1 ELSE 0 END) AS approximate_count,
                    SUM(CASE WHEN precision = 'precise' THEN 1 ELSE 0 END) AS precise_count,
                    SUM(CASE WHEN precision = 'moderate' THEN 1 ELSE 0 END) AS moderate_count,
                    MAX(captured_at) AS latest_captured_at,
                    ARRAY_AGG(device_id) AS device_ids
                FROM latest
                GROUP BY cell_geom
                ORDER BY device_count DESC, latest_captured_at DESC
                """
            ),
            {
                'org_id': org_id,
                'starts_at': window.starts_at,
                'ends_at': window.ends_at,
                'cell_size_degrees': cell_size_degrees,
            },
        )
        return [dict(row._mapping) for row in result]

    def source_label_for(self, event: LocationEvent) -> str:
        methods = list((event.source_methods or {}).get('methods', []))
        if event.is_ip_approximate or event.precision == LocationPrecision.APPROXIMATE:
            return 'Approximate IP / network context'
        if methods:
            return ' + '.join(method.replace('_', ' ').title() for method in methods)
        return 'Visible location check-in'
