from __future__ import annotations

from app.services.approval_workflow_service import ApprovalWorkflowService
from app.services.authorization_policy_service import AuthorizationPolicyService
from app.services.audit_log_service import AuditLogService
from app.services.audit_service import AuditService
from app.services.auth_identity_service import AuthIdentityService
from app.services.case_management_service import CaseManagementService
from app.services.case_evidence_service import CaseEvidenceService
from app.services.command_queue_service import CommandQueueService
from app.services.command_signing_service import CommandSigningService
from app.services.compliance_service import ComplianceService
from app.services.device_key_service import DeviceKeyService
from app.services.device_registry_service import DeviceRegistryService
from app.services.enrollment_service import EnrollmentService
from app.services.event_consumer_worker import EventConsumerWorker, build_default_event_worker
from app.services.event_publisher_service import EventPublisherService
from app.services.event_queue_service import EventQueue, SqlAlchemyEventQueueService
from app.services.evidence_export_bundle_service import EvidenceExportBundleService
from app.services.geofence_service import GeofenceService
from app.services.incident_service import IncidentService
from app.services.incident_state_machine import IncidentStateMachine
from app.services.integrity_verification_service import IntegrityVerificationService
from app.services.ip_enrichment_service import IpEnrichmentService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.location_confidence import LocationConfidenceService
from app.services.notification_event_service import NotificationEventService
from app.services.notification_service import FcmNotificationService, NotificationService
from app.services.notification_template_service import NotificationTemplateService
from app.services.observability_service import ObservabilityService
from app.services.ownership_access_service import OwnershipAccessService
from app.services.remote_action_service import RemoteActionService
from app.services.rule_action_executor import RuleActionExecutor
from app.services.rules_engine_service import RulesEngineService
from app.services.spatial_service import SpatialService
from app.services.signed_telemetry_service import SignedTelemetryService
from app.services.tenant_service import TenantService
from app.services.telemetry_service import TelemetryService


def get_audit_service() -> AuditService:
    return AuditService()


def get_authorization_policy_service() -> AuthorizationPolicyService:
    return AuthorizationPolicyService()


def get_approval_workflow_service() -> ApprovalWorkflowService:
    return ApprovalWorkflowService()


def get_location_confidence_service() -> LocationConfidenceService:
    return LocationConfidenceService()


def get_telemetry_service() -> TelemetryService:
    return TelemetryService(
        confidence_service=get_location_confidence_service(),
        signed_telemetry_service=get_signed_telemetry_service(),
    )


def get_notification_service() -> NotificationService:
    return FcmNotificationService()


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


def get_event_queue_service() -> EventQueue:
    return SqlAlchemyEventQueueService()


def get_event_publisher_service() -> EventPublisherService:
    return EventPublisherService(queue=get_event_queue_service())


def get_rule_action_executor() -> RuleActionExecutor:
    return RuleActionExecutor(
        notification_event_service=get_notification_event_service(),
        audit_log_service=get_audit_log_service(),
        command_queue_service=get_command_queue_service(),
    )


def get_location_ingestion_service() -> LocationIngestionService:
    return LocationIngestionService(
        signed_telemetry_service=get_signed_telemetry_service(),
        integrity_verification_service=get_integrity_verification_service(),
        ip_enrichment_service=get_ip_enrichment_service(),
        rules_engine_service=get_rules_engine_service(),
        geofence_service=get_geofence_service(),
    )


def get_case_management_service() -> CaseManagementService:
    return CaseManagementService(state_machine=IncidentStateMachine())


def get_case_evidence_service() -> CaseEvidenceService:
    return CaseEvidenceService()


def get_evidence_export_bundle_service() -> EvidenceExportBundleService:
    return EvidenceExportBundleService()


def get_remote_action_service() -> RemoteActionService:
    return RemoteActionService()


def get_notification_event_service() -> NotificationEventService:
    return NotificationEventService(provider=get_notification_service())


def get_geofence_service() -> GeofenceService:
    return GeofenceService()


def get_spatial_service() -> SpatialService:
    return SpatialService()


def get_ownership_access_service() -> OwnershipAccessService:
    return OwnershipAccessService()


def get_command_signing_service() -> CommandSigningService:
    return CommandSigningService()


def get_notification_template_service() -> NotificationTemplateService:
    return NotificationTemplateService()


def get_command_queue_service() -> CommandQueueService:
    return CommandQueueService(
        signing_service=get_command_signing_service(),
        notification_event_service=get_notification_event_service(),
        notification_template_service=get_notification_template_service(),
    )


def get_event_consumer_worker() -> EventConsumerWorker:
    return build_default_event_worker(
        queue=get_event_queue_service(),
        rules_engine=get_rules_engine_service(),
        action_executor=get_rule_action_executor(),
        event_publisher=get_event_publisher_service(),
    )


def get_observability_service() -> ObservabilityService:
    return ObservabilityService()


def get_compliance_service() -> ComplianceService:
    return ComplianceService()
