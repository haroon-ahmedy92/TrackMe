from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_service, get_incident_service
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import IncidentRecord, IncidentTimelineEvent
from app.schemas.incident import (
    ConfirmStolenRequest,
    IncidentRecordOut,
    IncidentResolutionRequest,
    IncidentTimelineEventOut,
    MarkDeviceLostRequest,
    RemoteLockDecisionRequest,
    RemoteWipeDecisionRequest,
)
from app.services.audit_service import AuditService
from app.services.incident_service import IncidentService

router = APIRouter(prefix='/incidents', tags=['incidents'])


@router.post('/mark-lost', response_model=IncidentRecordOut)
async def mark_lost(
    payload: MarkDeviceLostRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentRecordOut:
    try:
        incident = await incident_service.mark_lost(
            session=session,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return _record_out(incident)


@router.post('/{incident_id}/confirm-stolen', response_model=IncidentRecordOut)
async def confirm_stolen(
    incident_id: UUID,
    payload: ConfirmStolenRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentRecordOut:
    try:
        incident = await incident_service.confirm_stolen(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return _record_out(incident)


@router.post('/{incident_id}/remote-lock', response_model=dict)
async def remote_lock_decision(
    incident_id: UUID,
    payload: RemoteLockDecisionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    try:
        action = await incident_service.request_remote_lock(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return {'action_id': str(action.id), 'status': action.status.value}


@router.post('/{incident_id}/remote-wipe', response_model=dict)
async def remote_wipe_decision(
    incident_id: UUID,
    payload: RemoteWipeDecisionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    try:
        incident, action = await incident_service.request_remote_wipe(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc

    return {
        'incident_id': str(incident.id),
        'state': incident.state.value,
        'wipe_scheduled_at': incident.wipe_scheduled_at.isoformat() if incident.wipe_scheduled_at else None,
        'action_id': str(action.id) if action else None,
    }


@router.post('/{incident_id}/recover', response_model=IncidentRecordOut)
async def recover_incident(
    incident_id: UUID,
    payload: IncidentResolutionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentRecordOut:
    try:
        incident = await incident_service.recover(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return _record_out(incident)


@router.post('/{incident_id}/cancel', response_model=IncidentRecordOut)
async def cancel_incident(
    incident_id: UUID,
    payload: IncidentResolutionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentRecordOut:
    try:
        incident = await incident_service.cancel(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return _record_out(incident)


@router.post('/{incident_id}/decommission', response_model=IncidentRecordOut)
async def decommission_incident(
    incident_id: UUID,
    payload: IncidentResolutionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> IncidentRecordOut:
    try:
        incident = await incident_service.decommission(
            session=session,
            incident_id=incident_id,
            payload=payload,
            actor_sub=principal.subject,
            organization_id=principal.organization_id,
            audit_service=audit_service,
        )
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return _record_out(incident)


@router.get('/{incident_id}/timeline', response_model=list[IncidentTimelineEventOut])
async def incident_timeline(
    incident_id: UUID,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    incident_service: IncidentService = Depends(get_incident_service),
) -> list[IncidentTimelineEventOut]:
    try:
        timeline = await incident_service.timeline(session=session, incident_id=incident_id)
    except Exception as exc:
        raise _to_http_exception(exc) from exc
    return [_timeline_out(event) for event in timeline]


def _record_out(record: IncidentRecord) -> IncidentRecordOut:
    return IncidentRecordOut(
        incident_id=record.id,
        device_id=record.device_id,
        ticket_reference=record.ticket_reference,
        state=record.state.value,
        recovery_message=record.recovery_message,
        wipe_scheduled_at=record.wipe_scheduled_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _timeline_out(event: IncidentTimelineEvent) -> IncidentTimelineEventOut:
    return IncidentTimelineEventOut(
        id=event.id,
        incident_id=event.incident_id,
        state=event.state.value,
        action=event.action,
        summary=event.summary,
        metadata=event.metadata_json,
        occurred_at=event.occurred_at,
    )


def _to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, ValueError):
        detail = str(exc)
        code = status.HTTP_404_NOT_FOUND if detail.startswith('Unknown') else status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=code, detail=detail)
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Incident processing failed')
