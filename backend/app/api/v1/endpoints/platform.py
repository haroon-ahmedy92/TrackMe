from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_audit_log_service,
    get_auth_identity_service,
    get_case_evidence_service,
    get_case_management_service,
    get_compliance_service,
    get_device_key_service,
    get_device_registry_service,
    get_enrollment_service,
    get_event_publisher_service,
    get_evidence_export_bundle_service,
    get_geofence_service,
    get_ip_enrichment_service,
    get_location_ingestion_service,
    get_notification_event_service,
    get_observability_service,
    get_remote_action_service,
    get_rules_engine_service,
    get_spatial_service,
    get_tenant_service,
)
from app.core.security import Principal, Role, require_roles
from app.db.base import get_db_session
from app.db.models import AuditLog, GeofenceEvent, Incident, LocationEvent
from app.schemas.compliance import (
    AbuseReportCreateRequest,
    AbuseReportResponse,
    PlatformSettingsResponse,
    PrivacyDefaultsResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
)
from app.schemas.platform import (
    AuditLogResponse,
    AuditReportEntryResponse,
    AuditReportResponse,
    AuditLogChainVerificationResponse,
    AccessReviewReportResponse,
    CaseEvidenceChainResponse,
    CaseEvidenceEntryResponse,
    DeviceClusterResponse,
    DeviceKeyRegisterRequest,
    DeviceKeyRotateRequest,
    DeviceKeyResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    EnrollmentCreateRequest,
    EnrollmentResponse,
    IncidentAttachmentCreateRequest,
    IncidentAttachmentResponse,
    GeofenceCreateRequest,
    GeofenceEventResponse,
    GeofenceResponse,
    GeofenceUpdateRequest,
    IncidentCreateRequest,
    IncidentEvidenceExportRequest,
    IncidentEvidenceExportResponse,
    IncidentEventResponse,
    IncidentNoteCreateRequest,
    IncidentNoteResponse,
    IncidentNoteUpdateRequest,
    IncidentRemoteActionEvidenceResponse,
    IncidentRouteResponse,
    IncidentResponse,
    IncidentTransitionRequest,
    IpEnrichmentRequest,
    IpEnrichmentResponse,
    LocationEventPointResponse,
    LocationBatchIngestRequest,
    LocationBatchIngestResponse,
    LocationBatchIngestItemResponse,
    LocationIngestRequest,
    LocationIngestResponse,
    NotificationCreateRequest,
    NotificationResponse,
    ObservabilityAlertResponse,
    ObservabilityDashboardResponse,
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
from app.services.case_evidence_service import CaseEvidenceService
from app.services.case_management_service import CaseManagementService
from app.services.compliance_service import ComplianceService
from app.services.device_key_service import DeviceKeyService
from app.services.device_registry_service import DeviceRegistryService
from app.services.enrollment_service import EnrollmentService
from app.services.event_publisher_service import EventPublisherService
from app.services.evidence_export_bundle_service import EvidenceExportBundleService
from app.services.geofence_service import GeofenceService
from app.services.ip_enrichment_service import IpEnrichmentService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.notification_event_service import NotificationEventService
from app.services.observability_service import ObservabilityService
from app.services.remote_action_service import RemoteActionService
from app.services.rules_engine_service import RulesEngineService
from app.services.spatial_service import SpatialService
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
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> LocationIngestResponse:
    _assert_org_access(principal, payload.org_id)
    payload = payload.model_copy(update={'idempotency_key': idempotency_key or payload.idempotency_key})
    result = await service.ingest(session, payload)
    await event_publisher.publish_location_updated(
        session,
        location_event=result.event,
        rule_matches=result.rule_matches,
        suspicious_alerts=result.suspicious_alerts,
    )
    for geofence_event in getattr(result, 'geofence_events', []):
        await event_publisher.publish_geofence_transition(session, geofence_event=geofence_event)
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


@router.post('/locations/ingest-batch', response_model=LocationBatchIngestResponse)
async def ingest_location_batch(
    payload: LocationBatchIngestRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: LocationIngestionService = Depends(get_location_ingestion_service),
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> LocationBatchIngestResponse:
    results: list[LocationBatchIngestItemResponse] = []
    accepted_count = 0
    duplicate_count = 0
    failed_count = 0

    for item in payload.items:
        _assert_org_access(principal, item.org_id)
        try:
            result = await service.ingest(session, item)
            await event_publisher.publish_location_updated(
                session,
                location_event=result.event,
                rule_matches=result.rule_matches,
                suspicious_alerts=result.suspicious_alerts,
            )
            for geofence_event in getattr(result, 'geofence_events', []):
                await event_publisher.publish_geofence_transition(session, geofence_event=geofence_event)
            await audit_log_service.append(
                session,
                org_id=str(item.org_id),
                actor_sub=principal.subject,
                action='LOCATION_INGESTED',
                entity_type='location_event',
                entity_id=str(result.event.id),
                metadata={
                    'device_id': str(item.device_id),
                    'duplicate': result.duplicate,
                    'precision': item.precision.value,
                    'confidence_score': item.confidence_score,
                    'rule_matches': result.rule_matches,
                    'ip_approximate': result.event.is_ip_approximate,
                    'telemetry_digest_matches': result.telemetry_digest_matches,
                    'integrity_status': result.integrity_status,
                    'suspicious_alerts': result.suspicious_alerts,
                    'batched': True,
                },
            )
            if result.duplicate:
                duplicate_count += 1
            else:
                accepted_count += 1
            results.append(
                LocationBatchIngestItemResponse(
                    idempotency_key=item.idempotency_key,
                    event_id=result.event.id,
                    accepted=not result.duplicate,
                    duplicate=result.duplicate,
                    error=None,
                )
            )
        except ValueError as exc:
            failed_count += 1
            results.append(
                LocationBatchIngestItemResponse(
                    idempotency_key=item.idempotency_key,
                    event_id=None,
                    accepted=False,
                    duplicate=False,
                    error=str(exc),
                )
            )

    await session.commit()
    return LocationBatchIngestResponse(
        accepted_count=accepted_count,
        duplicate_count=duplicate_count,
        failed_count=failed_count,
        results=results,
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
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    _assert_org_access(principal, payload.org_id)
    incident = await service.open_case(session, payload)
    latest_event = (await service.list_case_events(session, incident.id, limit=1))[0]
    await event_publisher.publish_incident_state_changed(session, incident=incident, incident_event=latest_event)
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


@router.get('/incidents', response_model=list[IncidentResponse])
async def list_cases(
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
) -> list[IncidentResponse]:
    _assert_org_access(principal, org_id)
    incidents = await case_evidence_service.list_cases(session, org_id=org_id)
    return [_incident_response(incident) for incident in incidents]


@router.post('/cases/{incident_id}/confirm-stolen', response_model=IncidentResponse)
async def case_confirm_stolen(
    incident_id: UUID,
    payload: IncidentTransitionRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
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
    latest_event = (await service.list_case_events(session, incident.id, limit=1))[0]
    await event_publisher.publish_incident_state_changed(session, incident=incident, incident_event=latest_event)
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
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='recover', payload=payload, actor_sub=principal.subject
    )
    latest_event = (await service.list_case_events(session, incident.id, limit=1))[0]
    await event_publisher.publish_incident_state_changed(session, incident=incident, incident_event=latest_event)
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
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='cancel', payload=payload, actor_sub=principal.subject
    )
    latest_event = (await service.list_case_events(session, incident.id, limit=1))[0]
    await event_publisher.publish_incident_state_changed(session, incident=incident, incident_event=latest_event)
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
    event_publisher: EventPublisherService = Depends(get_event_publisher_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, incident.org_id)
    incident = await service.apply_transition_request(
        session, incident_id=incident_id, action='decommission', payload=payload, actor_sub=principal.subject
    )
    latest_event = (await service.list_case_events(session, incident.id, limit=1))[0]
    await event_publisher.publish_incident_state_changed(session, incident=incident, incident_event=latest_event)
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


@router.get('/cases/{incident_id}/notes', response_model=list[IncidentNoteResponse])
async def list_case_notes(
    incident_id: UUID,
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
) -> list[IncidentNoteResponse]:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, org_id)
    if incident.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    notes = await case_evidence_service.list_notes(session, incident_id=incident.id)
    return [_incident_note_response(note) for note in notes]


@router.post('/cases/{incident_id}/notes', response_model=IncidentNoteResponse)
async def create_case_note(
    incident_id: UUID,
    payload: IncidentNoteCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentNoteResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, payload.org_id)
    if incident.org_id != payload.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    note = await case_evidence_service.create_note(session, incident=incident, payload=payload, actor_sub=principal.subject)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='CASE_NOTE_CREATED',
        entity_type='incident_note',
        entity_id=str(note.id),
        metadata={'incident_id': str(incident.id), 'is_pinned': note.is_pinned},
    )
    await session.commit()
    return _incident_note_response(note)


@router.put('/cases/{incident_id}/notes/{note_id}', response_model=IncidentNoteResponse)
async def update_case_note(
    incident_id: UUID,
    note_id: UUID,
    payload: IncidentNoteUpdateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentNoteResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, payload.org_id)
    if incident.org_id != payload.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    note = await case_evidence_service.update_note(session, incident=incident, note_id=note_id, payload=payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='CASE_NOTE_UPDATED',
        entity_type='incident_note',
        entity_id=str(note.id),
        metadata={'incident_id': str(incident.id), 'is_pinned': note.is_pinned},
    )
    await session.commit()
    return _incident_note_response(note)


@router.get('/cases/{incident_id}/attachments', response_model=list[IncidentAttachmentResponse])
async def list_case_attachments(
    incident_id: UUID,
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
) -> list[IncidentAttachmentResponse]:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, org_id)
    if incident.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    attachments = await case_evidence_service.list_attachments(session, incident_id=incident.id)
    return [_incident_attachment_response(attachment) for attachment in attachments]


@router.post('/cases/{incident_id}/attachments', response_model=IncidentAttachmentResponse)
async def create_case_attachment(
    incident_id: UUID,
    payload: IncidentAttachmentCreateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentAttachmentResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, payload.org_id)
    if incident.org_id != payload.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    attachment = await case_evidence_service.create_attachment(
        session,
        incident=incident,
        payload=payload,
        actor_sub=principal.subject,
    )
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='CASE_ATTACHMENT_ADDED',
        entity_type='incident_attachment',
        entity_id=str(attachment.id),
        metadata={'incident_id': str(incident.id), 'file_name': attachment.file_name},
    )
    await session.commit()
    return _incident_attachment_response(attachment)


@router.get('/cases/{incident_id}/exports', response_model=list[IncidentEvidenceExportResponse])
async def list_case_exports(
    incident_id: UUID,
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    bundle_service: EvidenceExportBundleService = Depends(get_evidence_export_bundle_service),
) -> list[IncidentEvidenceExportResponse]:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, org_id)
    if incident.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    exports = await case_evidence_service.list_exports(session, incident_id=incident.id)
    return [_incident_export_response(export, bundle_service=bundle_service) for export in exports]


@router.post('/cases/{incident_id}/exports', response_model=IncidentEvidenceExportResponse)
async def create_case_export(
    incident_id: UUID,
    payload: IncidentEvidenceExportRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    bundle_service: EvidenceExportBundleService = Depends(get_evidence_export_bundle_service),
    spatial_service: SpatialService = Depends(get_spatial_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> IncidentEvidenceExportResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, payload.org_id)
    if incident.org_id != payload.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    export = await case_evidence_service.create_export(
        session,
        incident=incident,
        payload=payload,
        actor_sub=principal.subject,
        spatial_service=spatial_service,
        bundle_service=bundle_service,
    )
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='CASE_EVIDENCE_EXPORT_CREATED',
        entity_type='evidence_export',
        entity_id=str(export.id),
        metadata={'incident_id': str(incident.id), 'format': export.format.value, 'redact_fields': payload.redact_fields},
    )
    await session.commit()
    return _incident_export_response(export, bundle_service=bundle_service)


@router.get('/cases/{incident_id}/exports/{export_id}/download')
async def download_case_export(
    incident_id: UUID,
    export_id: UUID,
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    bundle_service: EvidenceExportBundleService = Depends(get_evidence_export_bundle_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> FileResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, org_id)
    if incident.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    export = next(
        (item for item in await case_evidence_service.list_exports(session, incident_id=incident.id) if item.id == export_id),
        None,
    )
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Unknown export_id')
    bundle_path = bundle_service.bundle_path(org_id=incident.org_id, incident_id=incident.id, export_id=export.id)
    if not bundle_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Export bundle not generated')
    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='CASE_EVIDENCE_EXPORT_DOWNLOADED',
        entity_type='evidence_export',
        entity_id=str(export.id),
        metadata={'incident_id': str(incident.id), 'bundle_name': bundle_path.name},
    )
    await session.commit()
    return FileResponse(
        path=bundle_path,
        media_type='application/zip',
        filename=bundle_path.name,
    )


@router.get('/cases/{incident_id}/evidence-chain', response_model=CaseEvidenceChainResponse)
async def case_evidence_chain(
    incident_id: UUID,
    org_id: UUID = Query(...),
    redact_fields: list[str] = Query(default=[]),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    service: CaseManagementService = Depends(get_case_management_service),
    case_evidence_service: CaseEvidenceService = Depends(get_case_evidence_service),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> CaseEvidenceChainResponse:
    incident = await service.get_case(session, incident_id)
    _assert_org_access(principal, org_id)
    if incident.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant access denied')
    chain = await case_evidence_service.build_chain(
        session,
        incident=incident,
        redact_fields=redact_fields,
        spatial_service=spatial_service,
    )
    return CaseEvidenceChainResponse(
        incident=IncidentResponse.model_validate(chain['incident']),
        actions_taken=[IncidentRemoteActionEvidenceResponse.model_validate(action) for action in chain['actions_taken']],
        notes=[IncidentNoteResponse.model_validate(note) for note in chain['notes']],
        attachments=[IncidentAttachmentResponse.model_validate(attachment) for attachment in chain['attachments']],
        exports=[IncidentEvidenceExportResponse.model_validate(export) for export in chain['exports']],
        entries=[CaseEvidenceEntryResponse.model_validate(entry) for entry in chain['entries']],
    )


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
        center_latitude=float(geofence.center_latitude),
        center_longitude=float(geofence.center_longitude),
        radius_meters=geofence.radius_meters,
        is_enabled=geofence.is_enabled,
        created_at=geofence.created_at,
    )


@router.get('/geofences', response_model=list[GeofenceResponse])
async def list_geofences(
    org_id: UUID = Query(...),
    device_id: UUID | None = Query(default=None),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    service: GeofenceService = Depends(get_geofence_service),
) -> list[GeofenceResponse]:
    _assert_org_access(principal, org_id)
    geofences = await service.list_geofences(session, org_id=org_id, device_id=device_id)
    return [
        GeofenceResponse(
            geofence_id=geofence.id,
            org_id=geofence.org_id,
            device_id=geofence.device_id,
            name=geofence.name,
            center_latitude=float(geofence.center_latitude),
            center_longitude=float(geofence.center_longitude),
            radius_meters=geofence.radius_meters,
            is_enabled=geofence.is_enabled,
            created_at=geofence.created_at,
        )
        for geofence in geofences
    ]


@router.put('/geofences/{geofence_id}', response_model=GeofenceResponse)
async def update_geofence(
    geofence_id: UUID,
    payload: GeofenceUpdateRequest,
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: GeofenceService = Depends(get_geofence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> GeofenceResponse:
    _assert_org_access(principal, payload.org_id)
    geofence = await service.update_geofence(session, geofence_id=geofence_id, payload=payload)
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='GEOFENCE_UPDATED',
        entity_type='geofence',
        entity_id=str(geofence.id),
        metadata={
            'name': geofence.name,
            'radius_meters': geofence.radius_meters,
            'device_id': str(geofence.device_id) if geofence.device_id else None,
            'is_enabled': geofence.is_enabled,
        },
    )
    await session.commit()
    return GeofenceResponse(
        geofence_id=geofence.id,
        org_id=geofence.org_id,
        device_id=geofence.device_id,
        name=geofence.name,
        center_latitude=float(geofence.center_latitude),
        center_longitude=float(geofence.center_longitude),
        radius_meters=geofence.radius_meters,
        is_enabled=geofence.is_enabled,
        created_at=geofence.created_at,
    )


@router.delete('/geofences/{geofence_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_geofence(
    geofence_id: UUID,
    org_id: UUID = Query(...),
    reason: str = Query(..., min_length=2, max_length=250),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY)),
    session: AsyncSession = Depends(get_db_session),
    service: GeofenceService = Depends(get_geofence_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> None:
    _assert_org_access(principal, org_id)
    geofence = await service.delete_geofence(session, geofence_id=geofence_id, org_id=org_id)
    await audit_log_service.append(
        session,
        org_id=str(org_id),
        actor_sub=principal.subject,
        action='GEOFENCE_DELETED',
        entity_type='geofence',
        entity_id=str(geofence.id),
        metadata={'name': geofence.name, 'reason': reason},
    )
    await session.commit()


@router.get('/devices/{device_id}/last-location', response_model=LocationEventPointResponse | None)
async def get_last_known_location(
    device_id: UUID,
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> LocationEventPointResponse | None:
    _assert_org_access(principal, org_id)
    event = await spatial_service.get_last_known_location(session, org_id=org_id, device_id=device_id)
    return _location_event_out(event, spatial_service) if event else None


@router.get('/devices/{device_id}/location-history', response_model=list[LocationEventPointResponse])
async def get_location_history(
    device_id: UUID,
    org_id: UUID = Query(...),
    starts_at: datetime | None = Query(default=None),
    ends_at: datetime | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> list[LocationEventPointResponse]:
    _assert_org_access(principal, org_id)
    history = await spatial_service.get_location_history(
        session,
        org_id=org_id,
        device_id=device_id,
        starts_at=starts_at,
        ends_at=ends_at,
        limit=limit,
    )
    return [_location_event_out(event, spatial_service) for event in history]


@router.get('/devices/{device_id}/geofence-events', response_model=list[GeofenceEventResponse])
async def get_device_geofence_events(
    device_id: UUID,
    org_id: UUID = Query(...),
    starts_at: datetime | None = Query(default=None),
    ends_at: datetime | None = Query(default=None),
    limit: int = Query(default=250, ge=1, le=1000),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> list[GeofenceEventResponse]:
    _assert_org_access(principal, org_id)
    window = spatial_service.normalize_window(starts_at=starts_at, ends_at=ends_at)
    events = await spatial_service.get_geofence_events(
        session,
        org_id=org_id,
        device_id=device_id,
        starts_at=window.starts_at,
        ends_at=window.ends_at,
        limit=limit,
    )
    return [_geofence_event_out(event, geofence_name) for event, geofence_name in events]


@router.get('/devices/clusters', response_model=list[DeviceClusterResponse])
async def get_device_clusters(
    org_id: UUID = Query(...),
    starts_at: datetime | None = Query(default=None),
    ends_at: datetime | None = Query(default=None),
    cell_size_meters: int = Query(default=10000, ge=500, le=100000),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER)),
    session: AsyncSession = Depends(get_db_session),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> list[DeviceClusterResponse]:
    _assert_org_access(principal, org_id)
    clusters = await spatial_service.get_device_clusters(
        session,
        org_id=org_id,
        starts_at=starts_at,
        ends_at=ends_at,
        cell_size_meters=cell_size_meters,
    )
    return [
        DeviceClusterResponse(
            cluster_id=str(row['cluster_id']),
            center_latitude=float(row['center_latitude']),
            center_longitude=float(row['center_longitude']),
            device_count=int(row['device_count']),
            approximate_count=int(row['approximate_count']),
            precise_count=int(row['precise_count']),
            moderate_count=int(row['moderate_count']),
            latest_captured_at=row['latest_captured_at'],
            device_ids=list(row['device_ids'] or []),
        )
        for row in clusters
    ]


@router.get('/cases/{incident_id}/route', response_model=IncidentRouteResponse)
async def get_incident_route(
    incident_id: UUID,
    org_id: UUID = Query(...),
    starts_at: datetime | None = Query(default=None),
    ends_at: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.OWNER, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    spatial_service: SpatialService = Depends(get_spatial_service),
) -> IncidentRouteResponse:
    _assert_org_access(principal, org_id)
    incident, points, geofence_events, window = await spatial_service.get_incident_route(
        session,
        org_id=org_id,
        incident_id=incident_id,
        starts_at=starts_at,
        ends_at=ends_at,
        limit=limit,
    )
    return IncidentRouteResponse(
        incident_id=incident.id,
        device_id=incident.device_id,
        started_at=window.starts_at,
        ended_at=window.ends_at,
        points=[_location_event_out(point, spatial_service) for point in points],
        geofence_events=[_geofence_event_out(event, geofence_name) for event, geofence_name in geofence_events],
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


@router.get('/observability/dashboard', response_model=ObservabilityDashboardResponse)
async def observability_dashboard(
    org_id: UUID = Query(...),
    window_hours: int = Query(default=24, ge=1, le=168),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> ObservabilityDashboardResponse:
    _assert_org_access(principal, org_id)
    return ObservabilityDashboardResponse(**(await observability_service.build_dashboard(session, org_id=org_id, window_hours=window_hours)))


@router.get('/observability/alerts', response_model=list[ObservabilityAlertResponse])
async def observability_alerts(
    org_id: UUID = Query(...),
    window_hours: int = Query(default=24, ge=1, le=168),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> list[ObservabilityAlertResponse]:
    _assert_org_access(principal, org_id)
    return [ObservabilityAlertResponse(**row) for row in await observability_service.detect_alerts(session, org_id=org_id, window_hours=window_hours)]


@router.get('/observability/access-review-report', response_model=AccessReviewReportResponse)
async def access_review_report(
    org_id: UUID = Query(...),
    window_hours: int = Query(default=168, ge=1, le=720),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> AccessReviewReportResponse:
    _assert_org_access(principal, org_id)
    return AccessReviewReportResponse(**(await observability_service.build_access_review_report(session, org_id=org_id, window_hours=window_hours)))


@router.get('/observability/audit-report', response_model=AuditReportResponse)
async def audit_report(
    org_id: UUID = Query(...),
    window_hours: int = Query(default=168, ge=1, le=720),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> AuditReportResponse:
    _assert_org_access(principal, org_id)
    report = await observability_service.build_audit_report(session, org_id=org_id, window_hours=window_hours)
    return AuditReportResponse(
        org_id=UUID(report['org_id']),
        window_hours=report['window_hours'],
        generated_at=datetime.fromisoformat(report['generated_at']),
        entries=[
            AuditReportEntryResponse(
                audit_id=entry['audit_id'],
                occurred_at=datetime.fromisoformat(entry['occurred_at']),
                actor_sub=entry['actor_sub'],
                action=entry['action'],
                entity_type=entry['entity_type'],
                entity_id=entry['entity_id'],
                reason=entry.get('reason'),
                result=entry.get('result'),
                request_id=entry.get('request_id'),
                device_id=entry.get('device_id'),
                privacy_preserving=entry.get('privacy_preserving', True),
                metadata=entry.get('metadata', {}),
            )
            for entry in report['entries']
        ],
    )


@router.get('/observability/audit-report/export')
async def export_audit_report(
    org_id: UUID = Query(...),
    window_hours: int = Query(default=168, ge=1, le=720),
    principal: Principal = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN, Role.ORG_ADMIN, Role.SECURITY, Role.AUDITOR)),
    session: AsyncSession = Depends(get_db_session),
    observability_service: ObservabilityService = Depends(get_observability_service),
) -> FileResponse:
    _assert_org_access(principal, org_id)
    report = await observability_service.build_audit_report(session, org_id=org_id, window_hours=window_hours)
    report_path = observability_service.export_audit_report(org_id=org_id, report=report)
    return FileResponse(path=report_path, media_type='application/json', filename=report_path.name)


@router.get('/settings', response_model=PlatformSettingsResponse)
async def get_platform_settings(
    org_id: UUID = Query(...),
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    compliance_service: ComplianceService = Depends(get_compliance_service),
) -> PlatformSettingsResponse:
    _assert_org_access(principal, org_id)
    settings_record = await compliance_service.get_or_create_settings(session, org_id=org_id)
    await session.commit()
    return PlatformSettingsResponse(
        org_id=org_id,
        timezone='Africa/Dar_es_Salaam',
        default_map_provider='google',
        retention_policy=RetentionPolicyResponse(
            location_event_days=settings_record.location_event_days,
            audit_log_days=settings_record.audit_log_days,
            incident_evidence_days=settings_record.incident_evidence_days,
        ),
        privacy_defaults=PrivacyDefaultsResponse(),
        updated_at=settings_record.updated_at,
        updated_by_sub=settings_record.updated_by_sub,
    )


@router.put('/settings/retention-policy', response_model=RetentionPolicyResponse)
async def update_retention_policy(
    payload: RetentionPolicyUpdateRequest,
    principal: Principal = Depends(require_roles(Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
    compliance_service: ComplianceService = Depends(get_compliance_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> RetentionPolicyResponse:
    _assert_org_access(principal, payload.org_id)
    settings_record = await compliance_service.update_retention_policy(
        session,
        payload=payload,
        actor_sub=principal.subject,
    )
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='RETENTION_POLICY_UPDATED',
        entity_type='tenant_settings',
        entity_id=str(settings_record.id),
        metadata={
            'reason': payload.reason,
            'location_event_days': payload.location_event_days,
            'audit_log_days': payload.audit_log_days,
            'incident_evidence_days': payload.incident_evidence_days,
        },
    )
    await session.commit()
    return RetentionPolicyResponse(
        location_event_days=settings_record.location_event_days,
        audit_log_days=settings_record.audit_log_days,
        incident_evidence_days=settings_record.incident_evidence_days,
    )


@router.post('/abuse-reports', response_model=AbuseReportResponse, status_code=status.HTTP_201_CREATED)
async def create_abuse_report(
    payload: AbuseReportCreateRequest,
    principal: Principal = Depends(require_roles(Role.OWNER, Role.ADMIN, Role.ORG_ADMIN, Role.SUPER_ADMIN, Role.SECURITY, Role.SECURITY_OPERATOR)),
    session: AsyncSession = Depends(get_db_session),
    compliance_service: ComplianceService = Depends(get_compliance_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service),
) -> AbuseReportResponse:
    _assert_org_access(principal, payload.org_id)
    try:
        report = await compliance_service.create_abuse_report(
            session,
            payload=payload,
            reported_by_sub=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await audit_log_service.append(
        session,
        org_id=str(payload.org_id),
        actor_sub=principal.subject,
        action='ABUSE_REPORT_SUBMITTED',
        entity_type='abuse_report',
        entity_id=str(report.id),
        metadata={
            'device_id': str(payload.device_id) if payload.device_id else None,
            'category': payload.category,
            'contact_email': payload.contact_email,
        },
    )
    await session.commit()
    return AbuseReportResponse(
        abuse_report_id=report.id,
        org_id=report.org_id,
        device_id=report.device_id,
        category=report.category,
        description=report.description,
        contact_email=report.contact_email,
        reported_by_sub=report.reported_by_sub,
        status=report.status,
        created_at=report.created_at,
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


def _location_event_out(event: LocationEvent, spatial_service: SpatialService) -> LocationEventPointResponse:
    methods = list((event.source_methods or {}).get('methods', []))
    return LocationEventPointResponse(
        event_id=event.id,
        device_id=event.device_id,
        captured_at=event.captured_at,
        latitude=float(event.latitude) if event.latitude is not None else None,
        longitude=float(event.longitude) if event.longitude is not None else None,
        accuracy_meters=float(event.accuracy_meters) if event.accuracy_meters is not None else None,
        precision=event.precision,
        confidence_score=event.confidence_score,
        source_methods=methods,
        is_ip_approximate=bool(event.is_ip_approximate),
        source_label=spatial_service.source_label_for(event),
    )


def _geofence_event_out(event: GeofenceEvent, geofence_name: str | None = None) -> GeofenceEventResponse:
    return GeofenceEventResponse(
        geofence_event_id=event.id,
        geofence_id=event.geofence_id,
        geofence_name=geofence_name,
        device_id=event.device_id,
        event_type=event.event_type,
        precision=event.precision,
        confidence_score=event.confidence_score,
        alert_emitted=event.alert_emitted,
        suppressed_reason=event.suppressed_reason,
        triggered_at=event.triggered_at,
    )


def _incident_note_response(note) -> IncidentNoteResponse:
    return IncidentNoteResponse(
        note_id=note.id,
        incident_id=note.incident_id,
        author_sub=note.author_sub,
        body=note.body,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _incident_attachment_response(attachment) -> IncidentAttachmentResponse:
    return IncidentAttachmentResponse(
        attachment_id=attachment.id,
        incident_id=attachment.incident_id,
        uploaded_by_sub=attachment.uploaded_by_sub,
        file_name=attachment.file_name,
        media_type=attachment.media_type,
        byte_size=attachment.byte_size,
        sha256=attachment.sha256,
        description=attachment.description,
        storage_key=attachment.storage_key,
        created_at=attachment.created_at,
    )


def _incident_export_response(export, *, bundle_service: EvidenceExportBundleService) -> IncidentEvidenceExportResponse:
    return IncidentEvidenceExportResponse(
        export_id=export.id,
        incident_id=export.incident_id,
        requested_by_sub=export.requested_by_sub,
        format=export.format,
        status=export.status,
        reason=export.reason,
        redact_fields=list(export.redact_fields_json.get('fields', [])),
        summary=export.summary_json,
        download_placeholder=bundle_service.download_url(
            incident_id=export.incident_id,
            export_id=export.id,
            org_id=export.org_id,
        ),
        created_at=export.created_at,
        generated_at=export.generated_at,
    )
