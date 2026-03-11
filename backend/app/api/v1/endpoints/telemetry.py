from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_audit_service, get_telemetry_service
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.schemas.telemetry import TelemetryCheckInRequest, TelemetryCheckInResponse
from app.services.audit_service import AuditService
from app.services.telemetry_service import TelemetryService

router = APIRouter(prefix='/telemetry', tags=['telemetry'])


@router.post('/check-ins', response_model=TelemetryCheckInResponse)
async def record_checkin(
    payload: TelemetryCheckInRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.INCIDENT_RESPONDER)),
    session: AsyncSession = Depends(get_db_session),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> TelemetryCheckInResponse:
    try:
        event = await telemetry_service.record_checkin(
            session=session,
            payload=payload,
            principal_org_id=principal.organization_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await audit_service.append_event(
        session=session,
        actor_sub=principal.subject,
        organization_id=principal.organization_id,
        action='CHECKIN_INGESTED',
        entity_type='device',
        entity_id=str(payload.device_id),
        metadata={
            'mode': payload.mode.value,
            'signal_count': len(payload.signals),
            'selected_confidence': event.confidence_score,
            'selected_method': event.method_label,
            'selected_is_approximate': event.is_approximate,
        },
    )
    await session.commit()

    return TelemetryCheckInResponse(
        accepted=True,
        selected_method_label=event.method_label,
        selected_confidence_score=event.confidence_score,
        selected_is_approximate=event.is_approximate,
    )
