from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_service
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import Device, RemoteActionRequest, RemoteActionStatus, RemoteActionType
from app.schemas.actions import RemoteActionRequestBody, RemoteActionResponse
from app.schemas.common import RemoteActionKind
from app.services.audit_service import AuditService

router = APIRouter(prefix='/actions', tags=['actions'])


@router.post('/remote-lock', response_model=RemoteActionResponse)
async def remote_lock(
    payload: RemoteActionRequestBody,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service),
) -> RemoteActionResponse:
    payload = payload.model_copy(update={'action': RemoteActionKind.LOCK})
    return await _create_remote_action(payload, principal, session, audit_service)


@router.post('/remote-wipe', response_model=RemoteActionResponse)
async def remote_wipe(
    payload: RemoteActionRequestBody,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    audit_service: AuditService = Depends(get_audit_service),
) -> RemoteActionResponse:
    payload = payload.model_copy(update={'action': RemoteActionKind.WIPE})
    if not payload.elevated_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Remote wipe requires elevated_confirmation=true',
        )
    if not payload.acknowledge_wipe_tradeoff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Remote wipe requires acknowledge_wipe_tradeoff=true',
        )
    return await _create_remote_action(payload, principal, session, audit_service)


async def _create_remote_action(
    payload: RemoteActionRequestBody,
    principal: Principal,
    session: AsyncSession,
    audit_service: AuditService,
) -> RemoteActionResponse:
    device_stmt = select(Device).where(Device.id == payload.device_id)
    device = (await session.execute(device_stmt)).scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Unknown device_id')
    if principal.organization_id is not None and str(device.organization_id) != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')

    if not device.is_policy_managed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Remote actions are allowed only for policy-managed devices',
        )

    now = datetime.now(timezone.utc)
    action_request = RemoteActionRequest(
        device_id=payload.device_id,
        action_type=RemoteActionType(payload.action.value),
        status=RemoteActionStatus.PENDING,
        ticket_reference=payload.ticket_reference,
        requested_by=principal.subject,
        reason=payload.reason,
        requested_at=now,
    )
    session.add(action_request)
    await session.flush()

    await audit_service.append_event(
        session=session,
        actor_sub=principal.subject,
        organization_id=principal.organization_id,
        action=f'REMOTE_{payload.action.value.upper()}_REQUESTED',
        entity_type='device',
        entity_id=str(payload.device_id),
        metadata={
            'ticket_reference': payload.ticket_reference,
            'reason': payload.reason,
            'elevated_confirmation': str(payload.elevated_confirmation),
            'acknowledge_wipe_tradeoff': str(payload.acknowledge_wipe_tradeoff),
        },
    )
    await session.commit()

    return RemoteActionResponse(
        action_id=action_request.id,
        status=action_request.status.value,
        requested_at=action_request.requested_at,
    )
