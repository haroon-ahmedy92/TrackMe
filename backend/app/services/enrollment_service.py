from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device, Enrollment, EnrollmentStatus
from app.schemas.platform import EnrollmentCreateRequest


class EnrollmentService:
    async def create_enrollment(self, session: AsyncSession, payload: EnrollmentCreateRequest) -> Enrollment:
        device = (await session.execute(select(Device).where(Device.id == payload.device_id))).scalar_one_or_none()
        if device is None:
            raise ValueError('Unknown device_id')
        if device.organization_id != payload.org_id:
            raise ValueError('Device does not belong to requested tenant org.')

        enrollment = Enrollment(
            org_id=payload.org_id,
            device_id=payload.device_id,
            status=EnrollmentStatus.ACTIVE,
            consent_version=payload.consent_version,
            enrolled_by_sub=payload.enrolled_by_sub,
            created_at=datetime.now(timezone.utc),
            revoked_at=None,
        )
        session.add(enrollment)
        await session.flush()
        return enrollment

    async def revoke_enrollment(self, session: AsyncSession, enrollment_id: UUID) -> Enrollment:
        enrollment = (await session.execute(select(Enrollment).where(Enrollment.id == enrollment_id))).scalar_one_or_none()
        if enrollment is None:
            raise ValueError('Unknown enrollment_id')
        enrollment.status = EnrollmentStatus.REVOKED
        enrollment.revoked_at = datetime.now(timezone.utc)
        await session.flush()
        return enrollment
