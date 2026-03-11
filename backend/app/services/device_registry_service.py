from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, EnrollmentType
from app.schemas.platform import DeviceRegisterRequest


class DeviceRegistryService:
    async def register_device(self, session: AsyncSession, payload: DeviceRegisterRequest) -> Device:
        record = Device(
            organization_id=payload.org_id,
            alias=payload.alias,
            enrollment_type=EnrollmentType(payload.enrollment_type),
            is_policy_managed=payload.is_policy_managed,
            consent_version=payload.consent_version,
            enrolled_at=datetime.now(timezone.utc),
        )
        session.add(record)
        await session.flush()
        return record

    async def get_device(self, session: AsyncSession, device_id: UUID) -> Device:
        stmt = select(Device).where(Device.id == device_id)
        device = (await session.execute(stmt)).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        return device

    async def list_devices(self, session: AsyncSession, org_id: UUID, limit: int = 200) -> list[Device]:
        stmt = select(Device).where(Device.organization_id == org_id).limit(limit)
        return list((await session.execute(stmt)).scalars().all())
