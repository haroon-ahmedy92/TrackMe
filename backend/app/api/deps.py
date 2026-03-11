from __future__ import annotations

from app.services.audit_log_service import AuditLogService
from app.services.audit_service import AuditService
from app.services.auth_identity_service import AuthIdentityService
from app.services.case_management_service import CaseManagementService
from app.services.device_key_service import DeviceKeyService
from app.services.device_registry_service import DeviceRegistryService
from app.services.enrollment_service import EnrollmentService
from app.services.geofence_service import GeofenceService
from app.services.incident_service import IncidentService
from app.services.incident_state_machine import IncidentStateMachine
from app.services.integrity_verification_service import IntegrityVerificationService
from app.services.ip_enrichment_service import IpEnrichmentService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.location_confidence import LocationConfidenceService
from app.services.notification_event_service import NotificationEventService
from app.services.notification_service import NoopNotificationService, NotificationService
from app.services.remote_action_service import RemoteActionService
from app.services.rules_engine_service import RulesEngineService
from app.services.signed_telemetry_service import SignedTelemetryService
from app.services.tenant_service import TenantService
from app.services.telemetry_service import TelemetryService


def get_audit_service() -> AuditService:
    return AuditService()


def get_location_confidence_service() -> LocationConfidenceService:
    return LocationConfidenceService()


def get_telemetry_service() -> TelemetryService:
    return TelemetryService(confidence_service=get_location_confidence_service())


def get_notification_service() -> NotificationService:
    return NoopNotificationService()


def get_incident_service() -> IncidentService:
    return IncidentService(
        state_machine=IncidentStateMachine(),
        notification_service=get_notification_service(),
    )


def get_audit_log_service() -> AuditLogService:
    return AuditLogService()


def get_auth_identity_service() -> AuthIdentityService:
    return AuthIdentityService()


def get_tenant_service() -> TenantService:
    return TenantService()


def get_device_registry_service() -> DeviceRegistryService:
    return DeviceRegistryService()


def get_enrollment_service() -> EnrollmentService:
    return EnrollmentService()


def get_device_key_service() -> DeviceKeyService:
    return DeviceKeyService()


def get_ip_enrichment_service() -> IpEnrichmentService:
    return IpEnrichmentService()


def get_integrity_verification_service() -> IntegrityVerificationService:
    return IntegrityVerificationService()


def get_signed_telemetry_service() -> SignedTelemetryService:
    return SignedTelemetryService()


def get_rules_engine_service() -> RulesEngineService:
    return RulesEngineService()


def get_location_ingestion_service() -> LocationIngestionService:
    return LocationIngestionService(
        signed_telemetry_service=get_signed_telemetry_service(),
        integrity_verification_service=get_integrity_verification_service(),
        ip_enrichment_service=get_ip_enrichment_service(),
        rules_engine_service=get_rules_engine_service(),
    )


def get_case_management_service() -> CaseManagementService:
    return CaseManagementService(state_machine=IncidentStateMachine())


def get_remote_action_service() -> RemoteActionService:
    return RemoteActionService()


def get_notification_event_service() -> NotificationEventService:
    return NotificationEventService(provider=get_notification_service())


def get_geofence_service() -> GeofenceService:
    return GeofenceService()
