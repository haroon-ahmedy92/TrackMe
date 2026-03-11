from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_audit_log_service,
    get_auth_identity_service,
    get_case_management_service,
    get_device_key_service,
    get_device_registry_service,
    get_enrollment_service,
    get_geofence_service,
    get_ip_enrichment_service,
    get_location_ingestion_service,
    get_notification_event_service,
    get_remote_action_service,
    get_rules_engine_service,
    get_tenant_service,
)
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import AuditLog
from app.schemas.platform import (
    AuditLogResponse,
    AuditLogChainVerificationResponse,
    DeviceKeyRegisterRequest,
    DeviceKeyRotateRequest,
    DeviceKeyResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    EnrollmentCreateRequest,
    EnrollmentResponse,
    GeofenceCreateRequest,
    GeofenceResponse,
    IncidentCreateRequest,
    IncidentEventResponse,
    IncidentResponse,
    IncidentTransitionRequest,
    IpEnrichmentRequest,
    IpEnrichmentResponse,
    LocationIngestRequest,
    LocationIngestResponse,
    NotificationCreateRequest,
    NotificationResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
    RemoteActionCreateRequest,
    RemoteActionResponse,
    RuleEvaluationResponse,
    UserResponse,
    UserUpsertRequest,
)
from app.services.audit_log_service import AuditLogService
from app.services.auth_identity_service import AuthIdentityService
from app.services.case_management_service import CaseManagementService
from app.services.device_key_service import DeviceKeyService
from app.services.device_registry_service import DeviceRegistryService
from app.services.enrollment_service import EnrollmentService
from app.services.geofence_service import GeofenceService
from app.services.ip_enrichment_service import IpEnrichmentService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.notification_event_service import NotificationEventService
from app.services.remote_action_service import RemoteActionService
from app.services.rules_engine_service import RulesEngineService
from app.services.tenant_service import TenantService

router = APIRouter(prefix='/platform', tags=['platform'])


@router.get('/identity/me', response_model=UserResponse | dict)
async def identity_me(
    principal: Principal = Depends(
        require_roles(
            Role.OWNER,
            Role.ADMIN,
            Role.SECURITY,
            Role.SUPER_ADMIN,
            Role.ORG_ADMIN,
            Role.INCIDENT_RESPONDER,
            Role.AUDITOR,
        )
    ),
    session: AsyncSession = Depends(get_db_session),
    identity_service: AuthIdentityService = Depends(get_auth_identity_service),
) -> UserResponse | dict:
    user = await identity_service.ensure_user(session, principal)
    await session.commit()
    if user is None:
        return {'subject': principal.subject, 'organization_id': principal.organization_id, 'roles': sorted(r.value for r in principal.roles)}
    return UserResponse(
        user_id=user.id,
        org_id=user.org_id,
        subject=user.subject,
        role=user.role,
        created_at=user.created_at,
    )


@router.post('/orgs', response_model=OrganizationResponse)
async def create_org(
    payload: OrganizationCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    tenant_service: TenantService = Depends(get_tenant_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> OrganizationResponse:
    org = await tenant_service.create_org(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(org.id),
        actor_sub=principal.subject,
        action='ORG_CREATED',
        entity_type='org',
        entity_id=str(org.id),
        metadata={'slug': org.slug, 'name': org.name},
    )
    await session.commit()
    return OrganizationResponse(org_id=org.id, slug=org.slug, name=org.name, created_at=org.created_at)


@router.post('/users', response_model=UserResponse)
async def upsert_user(
    payload: UserUpsertRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    tenant_service: TenantService = Depends(get_tenant_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> UserResponse:
    _assert_org_access(principal, payload.org_id)
    user = await tenant_service.upsert_user(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='USER_UPSERTED',
        entity_type='user',
        entity_id=str(user.id),
        metadata={'subject': payload.subject, 'role': payload.role.value},
    )
    await session.commit()
    return UserResponse(user_id=user.id, org_id=user.org_id, subject=user.subject, role=user.role, created_at=user.created_at)


@router.post('/devices', response_model=DeviceResponse)
async def register_device(
    payload: DeviceRegisterRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: DeviceRegistryService = Depends(get_device_registry_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DeviceResponse:
    _assert_org_access(principal, payload.org_id)
    device = await service.register_device(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='DEVICE_REGISTERED',
        entity_type='device',
        entity_id=str(device.id),
        metadata={'alias': payload.alias, 'policy_managed': payload.is_policy_managed},
    )
    await session.commit()
    return _device_response(device)


@router.get('/devices', response_model=list[DeviceResponse])
async def list_devices(
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: DeviceRegistryService = Depends(get_device_registry_service),
) -> list[DeviceResponse]:
    _assert_org_access(principal, org_id)
    devices = await service.list_devices(session, org_id=org_id)
    return [_device_response(d) for d in devices]


@router.post('/enrollments', response_model=EnrollmentResponse)
async def create_enrollment(
    payload: EnrollmentCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: EnrollmentService = Depends(get_enrollment_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> EnrollmentResponse:
    _assert_org_access(principal, payload.org_id)
    enrollment = await service.create_enrollment(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='ENROLLMENT_CREATED',
        entity_type='enrollment',
        entity_id=str(enrollment.id),
        metadata={'device_id': str(payload.device_id), 'consent_version': payload.consent_version},
    )
    await session.commit()
    return EnrollmentResponse(
        enrollment_id=enrollment.id,
        org_id=enrollment.org_id,
        device_id=enrollment.device_id,
        status=enrollment.status.value,
        created_at=enrollment.created_at,
    )


@router.post('/device-keys', response_model=DeviceKeyResponse)
async def register_device_key(
    payload: DeviceKeyRegisterRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: DeviceKeyService = Depends(get_device_key_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DeviceKeyResponse:
    _assert_org_access(principal, payload.org_id)
    key = await service.register_key(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='DEVICE_KEY_REGISTERED',
        entity_type='device_key',
        entity_id=str(key.id),
        metadata={'device_id': str(payload.device_id), 'key_id': payload.key_id, 'algorithm': payload.algorithm},
    )
    await session.commit()
    return DeviceKeyResponse(
        key_record_id=key.id,
        org_id=key.org_id,
        device_id=key.device_id,
        key_id=key.key_id,
        algorithm=key.algorithm,
        created_at=key.created_at,
    )


@router.post('/device-keys/rotate', response_model=DeviceKeyResponse)
async def rotate_device_key(
    payload: DeviceKeyRotateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: DeviceKeyService = Depends(get_device_key_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> DeviceKeyResponse:
    _assert_org_access(principal, payload.org_id)
    key = await service.rotate_key(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='DEVICE_KEY_ROTATED',
        entity_type='device_key',
        entity_id=str(key.id),
        metadata={'device_id': str(payload.device_id), 'key_id': payload.key_id, 'algorithm': payload.algorithm},
    )
    await session.commit()
    return DeviceKeyResponse(
        key_record_id=key.id,
        org_id=key.org_id,
        device_id=key.device_id,
        key_id=key.key_id,
        algorithm=key.algorithm,
        created_at=key.created_at,
    )


@router.post('/locations/ingest', response_model=LocationIngestResponse)
async def ingest_location(
    payload: LocationIngestRequest,
    idempotency_key: str | None = Header(default=None, alias='Idempotency-Key'),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: LocationIngestionService = Depends(get_location_ingestion_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> LocationIngestResponse:
    _assert_org_access(principal, payload.org_id)
    payload = payload.model_copy(update={'idempotency_key': idempotency_key or payload.idempotency_key})
    result = await service.ingest(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='LOCATION_INGESTED',
        entity_type='location_event',
        entity_id=str(result.event.id),
        metadata={
            'device_id': str(payload.device_id),
            'duplicate': result.duplicate,
            'precision': payload.precision.value,
            'confidence_score': payload.confidence_score,
            'rule_matches': result.rule_matches,
            'ip_approximate': result.event.is_ip_approximate,
            'telemetry_digest_matches': result.telemetry_digest_matches,
            'integrity_status': result.integrity_status,
            'suspicious_alerts': result.suspicious_alerts,
        },
    )
    await session.commit()
    return LocationIngestResponse(
        event_id=result.event.id,
        accepted=not result.duplicate,
        duplicate=result.duplicate,
        telemetry_verified=result.event.telemetry_verified,
        telemetry_digest_matches=result.telemetry_digest_matches,
        integrity_status=result.integrity_status,
        ip_is_approximate=result.event.is_ip_approximate,
        rule_matches=result.rule_matches,
        suspicious_alerts=result.suspicious_alerts,
    )


@router.post('/rules/evaluate', response_model=RuleEvaluationResponse)
async def evaluate_rules(
    payload: LocationIngestRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: RulesEngineService = Depends(get_rules_engine_service),
) -> RuleEvaluationResponse:
    _assert_org_access(principal, payload.org_id)
    result = await service.evaluate_location(session, payload)
    return RuleEvaluationResponse(rules=result.matches)


@router.post('/cases', response_model=IncidentResponse)
async def open_case(
    payload: IncidentCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    _assert_org_access(principal, payload.org_id)
    incident = await service.open_case(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='INCIDENT_OPENED',
        entity_type='incident',
        entity_id=str(incident.id),
        metadata={'device_id': str(payload.device_id), 'ticket_reference': payload.ticket_reference},
    )
    await session.commit()
    return _incident_response(incident)


@router.post('/cases/{incident_id}/confirm-stolen', response_model=IncidentResponse)
async def case_confirm_stolen(
    incident_id: UUID,
    payload: IncidentTransitionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session,
        incident_id=incident_id,
        action='confirm_stolen',
        payload=payload,
        actor_sub=principal.subject,
    )
    _assert_org_access(principal, incident.org_id)
    await audit_log_service.append(
        session,
        org_id=str(incident.org_id),
        actor_sub=principal.subject,
        action='INCIDENT_CONFIRMED_STOLEN',
        entity_type='incident',
        entity_id=str(incident.id),
        metadata={'reason': payload.reason, 'elevated_confirmation': payload.elevated_confirmation},
    )
    await session.commit()
    return _incident_response(incident)


@router.post('/cases/{incident_id}/recover', response_model=IncidentResponse)
async def case_recover(
    incident_id: UUID,
    payload: IncidentTransitionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='recover', payload=payload, actor_sub=principal.subject
    )
    _assert_org_access(principal, incident.org_id)
    await audit_log_service.append(
        session,
        org_id=str(incident.org_id),
        actor_sub=principal.subject,
        action='INCIDENT_RECOVERED',
        entity_type='incident',
        entity_id=str(incident.id),
        metadata={'reason': payload.reason},
    )
    await session.commit()
    return _incident_response(incident)


@router.post('/cases/{incident_id}/cancel', response_model=IncidentResponse)
async def case_cancel(
    incident_id: UUID,
    payload: IncidentTransitionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='cancel', payload=payload, actor_sub=principal.subject
    )
    _assert_org_access(principal, incident.org_id)
    await audit_log_service.append(
        session,
        org_id=str(incident.org_id),
        actor_sub=principal.subject,
        action='INCIDENT_CANCELLED',
        entity_type='incident',
        entity_id=str(incident.id),
        metadata={'reason': payload.reason},
    )
    await session.commit()
    return _incident_response(incident)


@router.post('/cases/{incident_id}/decommission', response_model=IncidentResponse)
async def case_decommission(
    incident_id: UUID,
    payload: IncidentTransitionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='decommission', payload=payload, actor_sub=principal.subject
    )
    _assert_org_access(principal, incident.org_id)
    await audit_log_service.append(
        session,
        org_id=str(incident.org_id),
        actor_sub=principal.subject,
        action='INCIDENT_DECOMMISSIONED',
        entity_type='incident',
        entity_id=str(incident.id),
        metadata={'reason': payload.reason},
    )
    await session.commit()
    return _incident_response(incident)


@router.get('/cases/{incident_id}/events', response_model=list[IncidentEventResponse])
async def case_events(
    incident_id: UUID,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
) -> list[IncidentEventResponse]:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    events = await service.list_case_events(session, incident_id)
    return [
        IncidentEventResponse(
            incident_event_id=e.id,
            incident_id=e.incident_id,
            state=e.state,
            action=e.action,
            summary=e.summary,
            metadata=e.metadata_json,
            occurred_at=e.occurred_at,
        )
        for e in events
    ]


@router.post('/remote-actions', response_model=RemoteActionResponse)
async def create_remote_action(
    payload: RemoteActionCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: RemoteActionService = Depends(get_remote_action_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> RemoteActionResponse:
    _assert_org_access(principal, payload.org_id)
    action = await service.request_action(session, payload, requested_by_sub=principal.subject)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action=f'REMOTE_{action.action_kind.value.upper()}_REQUESTED',
        entity_type='remote_action',
        entity_id=str(action.id),
        metadata={
            'device_id': str(payload.device_id),
            'incident_id': str(payload.incident_id) if payload.incident_id else None,
            'reason': payload.reason,
            'delayed_until': payload.delayed_until.isoformat() if payload.delayed_until else None,
            'elevated_confirmation': payload.elevated_confirmation,
            'acknowledge_wipe_tradeoff': payload.acknowledge_wipe_tradeoff,
        },
    )
    await session.commit()
    return RemoteActionResponse(
        remote_action_id=action.id,
        org_id=action.org_id,
        device_id=action.device_id,
        incident_id=action.incident_id,
        action_kind=action.action_kind,
        state=action.state.value,
        delayed_until=action.delayed_until,
        requested_at=action.requested_at,
    )


@router.post('/notifications', response_model=NotificationResponse)
async def create_notification(
    payload: NotificationCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: NotificationEventService = Depends(get_notification_event_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> NotificationResponse:
    _assert_org_access(principal, payload.org_id)
    event = await service.create_and_send(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='NOTIFICATION_ENQUEUED',
        entity_type='notification_event',
        entity_id=str(event.id),
        metadata={'status': event.status.value, 'channel': payload.channel, 'template': payload.template},
    )
    await session.commit()
    return NotificationResponse(notification_event_id=event.id, status=event.status.value, created_at=event.created_at)


@router.post('/geofences', response_model=GeofenceResponse)
async def create_geofence(
    payload: GeofenceCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: GeofenceService = Depends(get_geofence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> GeofenceResponse:
    _assert_org_access(principal, payload.org_id)
    geofence = await service.create_geofence(session, payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='GEOFENCE_CREATED',
        entity_type='geofence',
        entity_id=str(geofence.id),
        metadata={
            'name': geofence.name,
            'radius_meters': geofence.radius_meters,
            'device_id': str(geofence.device_id) if geofence.device_id else None,
        },
    )
    await session.commit()
    return GeofenceResponse(
        geofence_id=geofence.id,
        org_id=geofence.org_id,
        device_id=geofence.device_id,
        name=geofence.name,
        radius_meters=geofence.radius_meters,
        is_enabled=geofence.is_enabled,
        created_at=geofence.created_at,
    )


@router.post('/ip/enrich', response_model=IpEnrichmentResponse)
async def ip_enrich(
    payload: IpEnrichmentRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    service: IpEnrichmentService = Depends(get_ip_enrichment_service),
) -> IpEnrichmentResponse:
    result = await service.approximate(payload.ip_address)
    return IpEnrichmentResponse(
        ip_address=result.ip_address,
        is_approximate=result.is_approximate,
        country=result.country,
        city=result.city,
        latitude=result.latitude,
        longitude=result.longitude,
        accuracy_km=result.accuracy_km,
    )


@router.get('/audit-logs', response_model=list[AuditLogResponse])
async def list_audit_logs(
    org_id: UUID = Query(...),
    limit: int = Query(default=200, ge=1, le=1000),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
) -> list[AuditLogResponse]:
    _assert_org_access(principal, org_id)
    stmt = select(AuditLog).where(AuditLog.org_id == org_id).order_by(desc(AuditLog.occurred_at)).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        AuditLogResponse(
            audit_id=row.id,
            org_id=row.org_id,
            actor_sub=row.actor_sub,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            metadata=row.metadata_json,
            occurred_at=row.occurred_at,
            previous_hash=row.previous_hash,
            event_hash=row.event_hash,
        )
        for row in rows
    ]


def _assert_org_access(principal: Principal, org_id: UUID) -> None:
    if Role.SUPER_ADMIN in principal.roles:
        return
    if principal.organization_id is None or principal.organization_id != str(org_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')


@router.get('/audit-logs/verify', response_model=AuditLogChainVerificationResponse)
async def verify_audit_log_chain(
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> AuditLogChainVerificationResponse:
    _assert_org_access(principal, org_id)
    verified, checked_events, broken_at_audit_id, reason = await audit_log_service.verify_chain(
        session,
        org_id=str(org_id),
    )
    return AuditLogChainVerificationResponse(
        org_id=org_id,
        verified=verified,
        checked_events=checked_events,
        broken_at_audit_id=UUID(broken_at_audit_id) if broken_at_audit_id else None,
        reason=reason,
    )


def _device_response(device) -> DeviceResponse:
    return DeviceResponse(
        device_id=device.id,
        org_id=device.organization_id,
        alias=device.alias,
        enrollment_type=device.enrollment_type.value,
        is_policy_managed=device.is_policy_managed,
        enrolled_at=device.enrolled_at,
    )


def _incident_response(incident) -> IncidentResponse:
    return IncidentResponse(
        incident_id=incident.id,
        org_id=incident.org_id,
        device_id=incident.device_id,
        ticket_reference=incident.ticket_reference,
        state=incident.state,
        recovery_message=incident.recovery_message,
        lost_mode_until=incident.lost_mode_until,
        wipe_scheduled_at=incident.wipe_scheduled_at,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )
