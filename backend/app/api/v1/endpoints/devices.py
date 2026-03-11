from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_service
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import Device, EnrollmentType
from app.schemas.device import DeviceEnrollmentRequest, DeviceEnrollmentResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix='/devices', tags=['devices'])


@router.post('/enroll', response_model=DeviceEnrollmentResponse)
async def enroll_device(
    payload: DeviceEnrollmentRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service),
) -> DeviceEnrollmentResponse:
    if Role.SUPER_ADMIN not in principal.roles:
        if principal.organization_id is None:
            raise HTTPException(status_code=403, detail='Missing tenant scope')
        principal_org = UUID(principal.organization_id)
        if payload.organization_id is None:
            payload = payload.model_copy(update={'organization_id': principal_org})
        if payload.organization_id != principal_org:
            raise HTTPException(status_code=403, detail='Tenant access denied')

    now = datetime.now(timezone.utc)

    device = Device(
        alias=payload.alias,
        organization_id=payload.organization_id,
        enrollment_type=EnrollmentType(payload.enrollment_type.value),
        is_policy_managed=payload.is_policy_managed,
        consent_version=payload.consent_version,
        enrolled_at=now,
    )
    session.add(device)
    await session.flush()

    await audit_service.append_event(
        session=session,
        actor_sub=principal.subject,
        organization_id=principal.organization_id,
        action='DEVICE_ENROLLED',
        entity_type='device',
        entity_id=str(device.id),
        metadata={
            'enrollment_type': payload.enrollment_type.value,
            'policy_managed': payload.is_policy_managed,
        },
    )
    await session.commit()

    return DeviceEnrollmentResponse(device_id=device.id, enrolled_at=device.enrolled_at)
