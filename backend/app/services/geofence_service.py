from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Geofence
from app.schemas.platform import GeofenceCreateRequest


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
        return geofence
