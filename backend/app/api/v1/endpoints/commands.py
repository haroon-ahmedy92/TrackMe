from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_audit_log_service,
    get_command_queue_service,
    get_event_publisher_service,
    get_signed_telemetry_service,
)
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.schemas.commands import (
    CommandAckRequest,
    CommandAckResponse,
    CommandEnvelopeResponse,
    CommandQueueRequest,
    CommandRetryResponse,
    DeviceCommandSyncRequest,
    DevicePushTokenRegisterRequest,
    DevicePushTokenResponse,
)
from app.services.audit_log_service import AuditLogService
from app.services.command_queue_service import CommandQueueService
from app.services.event_publisher_service import EventPublisherService
from app.services.signed_telemetry_service import SignedTelemetryService

router = APIRouter(prefix='/commands', tags=['commands'])


@router.post('', response_model=CommandEnvelopeResponse)
async def queue_command(
    payload: CommandQueueRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CommandQueueService = Depends(get_command_queue_service),
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> CommandEnvelopeResponse:
    _assert_org_access(principal, payload.org_id)
    try:
        action = await service.queue_command(session, payload, actor_sub=principal.subject)
        await service.retry_pending_commands(session, org_id=payload.org_id, device_id=payload.device_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await event_publisher.schedule_command_pending_check(session, action=action)

    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action=f'COMMAND_{action.action_kind.value.upper()}_QUEUED',
        entity_type='remote_action',
        entity_id=str(action.id),
        metadata={
            'device_id': str(payload.device_id),
            'incident_id': str(payload.incident_id) if payload.incident_id else None,
            'reason': payload.reason,
            'expires_at': action.expires_at.isoformat() if action.expires_at else None,
        },
    )
    await session.commit()
    return service._to_envelope(action)


@router.post('/device-tokens', response_model=DevicePushTokenResponse)
async def register_device_push_token(
    payload: DevicePushTokenRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CommandQueueService = Depends(get_command_queue_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DevicePushTokenResponse:
    try:
        token = await service.register_push_token(session, payload)
        await service.retry_pending_commands(session, org_id=payload.org_id, device_id=payload.device_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=f'device:{payload.key_id}',
        action='DEVICE_PUSH_TOKEN_REGISTERED',
        entity_type='device_push_token',
        entity_id=str(token.id),
        metadata={'device_id': str(payload.device_id), 'app_version': payload.app_version},
    )
    await session.commit()
    return DevicePushTokenResponse(
        push_token_id=token.id,
        org_id=token.org_id,
        device_id=token.device_id,
        key_id=token.key_id,
        is_active=token.is_active,
        last_seen_at=token.last_seen_at,
    )


@router.post('/sync', response_model=list[CommandEnvelopeResponse])
async def sync_pending_commands(
    payload: DeviceCommandSyncRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CommandQueueService = Depends(get_command_queue_service),
) -> list[CommandEnvelopeResponse]:
    try:
        commands = await service.get_pending_commands(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await session.commit()
    return commands


@router.post('/{command_id}/ack', response_model=CommandAckResponse)
async def acknowledge_command(
    command_id: UUID,
    payload: CommandAckRequest,
    session: AsyncSession = Depends(get_db_session),
    service: CommandQueueService = Depends(get_command_queue_service),
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    signed_telemetry_service: SignedTelemetryService = Depends(get_signed_telemetry_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> CommandAckResponse:
    verification = await signed_telemetry_service.verify_command_ack_request(
        session,
        command_id=command_id,
        device_id=payload.device_id,
        payload=payload,
    )
    if not verification.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid signed command acknowledgement: {verification.reason}',
        )
    try:
        action = await service.acknowledge_command(session, command_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await event_publisher.publish_command_acknowledged(session, action=action)

    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=f'device:{payload.key_id}',
        action=f'COMMAND_{payload.status.value.upper()}_RECORDED',
        entity_type='remote_action',
        entity_id=str(action.id),
        metadata={'device_id': str(payload.device_id), 'error_message': payload.error_message, 'metadata': payload.metadata},
    )
    await session.commit()
    return CommandAckResponse(remote_action_id=action.id, status=action.state, updated_at=action.updated_at)


@router.post('/retry-dispatch', response_model=CommandRetryResponse)
async def retry_dispatch(
    org_id: UUID,
    device_id: UUID | None = None,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CommandQueueService = Depends(get_command_queue_service),
) -> CommandRetryResponse:
    _assert_org_access(principal, org_id)
    result = await service.retry_pending_commands(session, org_id=org_id, device_id=device_id)
    await session.commit()
    return CommandRetryResponse(
        processed=result.processed,
        sent=result.sent,
        failed=result.failed,
        expired=result.expired,
    )


def _assert_org_access(principal: Principal, org_id: UUID) -> None:
    if Role.SUPER_ADMIN in principal.roles:
        return
    if principal.organization_id is None or principal.organization_id != str(org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
