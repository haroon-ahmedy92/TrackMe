from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import (
    ApprovalStatus,
    EvidenceExportFormat,
    EvidenceExportStatus,
    GeofenceEventType,
    IncidentCaseState,
    LocationPrecision,
    PolicyActionType,
    RemoteActionKind,
    RemoteActionState,
    UserRole,
)
from app.schemas.common import Mode


class OrganizationCreateRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=180)


class OrganizationResponse(BaseModel):
    org_id: UUID
    slug: str
    name: str
    created_at: datetime


class UserUpsertRequest(BaseModel):
    org_id: UUID
    subject: str = Field(min_length=2, max_length=150)
    role: UserRole
    display_name: str | None = Field(default=None, max_length=140)
    email: str | None = Field(default=None, max_length=200)


class UserResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    subject: str
    role: UserRole
    created_at: datetime


class DeviceRegisterRequest(BaseModel):
    org_id: UUID
    alias: str = Field(min_length=1, max_length=120)
    enrollment_type: str = Field(min_length=3, max_length=32)
    is_policy_managed: bool = False
    consent_version: str = Field(min_length=1, max_length=40)


class DeviceResponse(BaseModel):
    device_id: UUID
    org_id: UUID | None
    alias: str
    enrollment_type: str
    is_policy_managed: bool
    enrolled_at: datetime
    last_seen_trust_status: str | None = None
    last_seen_trust_summary: str | None = None
    last_seen_trust_reasons: list[str] = Field(default_factory=list)


class TrustSignalsRequest(BaseModel):
    device_trust_status: str = Field(min_length=4, max_length=24)
    device_trust_summary: str = Field(min_length=4, max_length=280)
    device_trust_reasons: list[str] = Field(default_factory=list)
    integrity_status: str = Field(min_length=2, max_length=64)
    integrity_trusted: bool
    integrity_token_present: bool
    app_debug_build: bool
    app_debuggable: bool
    root_suspicion: bool
    mock_location_suspicion: bool
    key_hardware_backed: bool
    attestation_declared: bool


class DeviceTrustStatusResponse(BaseModel):
    device_id: UUID
    org_id: UUID
    status: str
    summary: str
    reasons: list[str] = Field(default_factory=list)
    integrity_status: str | None = None
    root_suspicion: bool = False
    debug_suspicion: bool = False
    mock_location_suspicion: bool = False
    trusted_telemetry_seen: bool = False
    observed_at: datetime | None = None


class EnrollmentCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    consent_version: str = Field(min_length=1, max_length=40)
    enrolled_by_sub: str = Field(min_length=2, max_length=150)


class EnrollmentResponse(BaseModel):
    enrollment_id: UUID
    org_id: UUID
    device_id: UUID
    status: str
    created_at: datetime


class DeviceKeyRegisterRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=2, max_length=80)
    public_key_pem: str = Field(min_length=16)
    algorithm: str = Field(min_length=3, max_length=32)
    is_hardware_backed: bool = False
    attestation_format: str | None = Field(default=None, max_length=48)
    attestation_record: str | None = Field(default=None, max_length=12000)
    rotate_existing_active: bool = True


class DeviceKeyResponse(BaseModel):
    key_record_id: UUID
    org_id: UUID
    device_id: UUID
    key_id: str
    algorithm: str
    is_active: bool
    is_hardware_backed: bool
    attestation_format: str | None
    revoked_at: datetime | None = None
    created_at: datetime


class DeviceKeyRotateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=2, max_length=80)
    public_key_pem: str = Field(min_length=16)
    algorithm: str = Field(min_length=3, max_length=32)
    is_hardware_backed: bool = False
    attestation_format: str | None = Field(default=None, max_length=48)
    attestation_record: str | None = Field(default=None, max_length=12000)


class DeviceKeyRevokeRequest(BaseModel):
    org_id: UUID
    reason: str = Field(min_length=4, max_length=280)


class LocationIngestRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    mode: Mode
    idempotency_key: str = Field(min_length=8, max_length=120)
    captured_at: datetime
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = Field(default=None, gt=0)
    precision: LocationPrecision
    confidence_score: int | None = Field(default=None, ge=0, le=100)
    source_methods: list[str] = Field(default_factory=list)
    network_type: str | None = Field(default=None, max_length=24)
    battery_percent: int | None = Field(default=None, ge=0, le=100)
    motion_state: str | None = Field(default=None, max_length=24)
    trust_signals: TrustSignalsRequest | None = None
    telemetry_signature: str | None = None
    telemetry_algorithm: str | None = Field(default=None, min_length=3, max_length=40)
    telemetry_key_id: str | None = None
    telemetry_payload_hash: str | None = Field(default=None, min_length=32, max_length=128)
    integrity_verdict: str | None = Field(default=None, max_length=64)
    ip_address: str | None = Field(default=None, max_length=64)


class LocationIngestResponse(BaseModel):
    event_id: UUID
    accepted: bool
    duplicate: bool
    telemetry_verified: bool
    telemetry_digest_matches: bool
    integrity_status: str
    trust_status: str
    trust_summary: str
    trust_reasons: list[str] = Field(default_factory=list)
    ip_is_approximate: bool
    rule_matches: list[str] = Field(default_factory=list)
    suspicious_alerts: list[str] = Field(default_factory=list)


class LocationBatchIngestRequest(BaseModel):
    items: list[LocationIngestRequest] = Field(default_factory=list, min_length=1, max_length=100)


class LocationBatchIngestItemResponse(BaseModel):
    idempotency_key: str
    event_id: UUID | None = None
    accepted: bool
    duplicate: bool
    error: str | None = None


class LocationBatchIngestResponse(BaseModel):
    accepted_count: int
    duplicate_count: int
    failed_count: int
    results: list[LocationBatchIngestItemResponse] = Field(default_factory=list)


class IncidentCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    ticket_reference: str = Field(min_length=2, max_length=80)
    recovery_message: str = Field(min_length=2, max_length=280)
    assigned_operator_sub: str | None = Field(default=None, min_length=2, max_length=150)
    lost_mode_until: datetime | None = None


class IncidentTransitionRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=250)
    elevated_confirmation: bool = False
    delayed_until: datetime | None = None


class IncidentResponse(BaseModel):
    incident_id: UUID
    org_id: UUID
    device_id: UUID
    ticket_reference: str
    state: IncidentCaseState
    assigned_operator_sub: str | None = None
    recovery_message: str | None
    lost_mode_until: datetime | None
    wipe_scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentAssignmentRequest(BaseModel):
    org_id: UUID
    operator_sub: str = Field(min_length=2, max_length=150)
    reason: str = Field(min_length=4, max_length=280)


class IncidentNoteCreateRequest(BaseModel):
    org_id: UUID
    body: str = Field(min_length=2, max_length=4000)
    is_pinned: bool = False


class IncidentNoteUpdateRequest(BaseModel):
    org_id: UUID
    body: str = Field(min_length=2, max_length=4000)
    is_pinned: bool = False


class IncidentNoteResponse(BaseModel):
    note_id: UUID
    incident_id: UUID
    author_sub: str
    body: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


class IncidentAttachmentCreateRequest(BaseModel):
    org_id: UUID
    file_name: str = Field(min_length=1, max_length=180)
    media_type: str = Field(min_length=3, max_length=120)
    byte_size: int = Field(ge=1)
    sha256: str | None = Field(default=None, min_length=16, max_length=128)
    description: str | None = Field(default=None, max_length=280)
    storage_key: str | None = Field(default=None, max_length=220)


class IncidentAttachmentResponse(BaseModel):
    attachment_id: UUID
    incident_id: UUID
    uploaded_by_sub: str
    file_name: str
    media_type: str
    byte_size: int
    sha256: str | None
    description: str | None
    storage_key: str | None
    created_at: datetime


class IncidentEvidenceExportRequest(BaseModel):
    org_id: UUID
    format: EvidenceExportFormat
    reason: str = Field(min_length=2, max_length=280)
    redact_fields: list[str] = Field(default_factory=list)


class EvidenceShareRequest(BaseModel):
    org_id: UUID
    recipient_label: str = Field(min_length=2, max_length=180)
    reason: str = Field(min_length=4, max_length=280)


class EvidenceShareResponse(BaseModel):
    export_id: UUID
    incident_id: UUID
    recipient_label: str
    reason: str
    shared_by_sub: str
    shared_at: datetime


class IncidentEvidenceExportResponse(BaseModel):
    export_id: UUID
    incident_id: UUID
    requested_by_sub: str
    format: EvidenceExportFormat
    status: EvidenceExportStatus
    reason: str
    redact_fields: list[str] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    download_placeholder: str | None = None
    approval_request_id: UUID | None = None
    policy_reason: str | None = None
    created_at: datetime
    generated_at: datetime | None


class IncidentEventResponse(BaseModel):
    incident_event_id: UUID
    incident_id: UUID
    state: IncidentCaseState
    action: str
    summary: str
    metadata: dict
    occurred_at: datetime


class GeofenceCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID | None = None
    name: str = Field(min_length=2, max_length=120)
    radius_meters: int = Field(ge=25, le=10000)
    center_latitude: float
    center_longitude: float


class GeofenceUpdateRequest(BaseModel):
    org_id: UUID
    device_id: UUID | None = None
    name: str = Field(min_length=2, max_length=120)
    radius_meters: int = Field(ge=25, le=10000)
    center_latitude: float
    center_longitude: float
    is_enabled: bool = True


class GeofenceResponse(BaseModel):
    geofence_id: UUID
    org_id: UUID
    device_id: UUID | None
    name: str
    center_latitude: float
    center_longitude: float
    radius_meters: int
    is_enabled: bool
    created_at: datetime


class LocationEventPointResponse(BaseModel):
    event_id: UUID
    device_id: UUID
    captured_at: datetime
    latitude: float | str | None
    longitude: float | str | None
    accuracy_meters: float | str | None
    precision: LocationPrecision
    confidence_score: int | None
    source_methods: list[str] = Field(default_factory=list)
    is_ip_approximate: bool
    source_label: str
    approximate_label: str | None = None
    staleness_label: str | None = None


class GeofenceEventResponse(BaseModel):
    geofence_event_id: UUID
    geofence_id: UUID
    geofence_name: str | None = None
    device_id: UUID
    event_type: GeofenceEventType
    precision: LocationPrecision
    confidence_score: int | None
    alert_emitted: bool
    suppressed_reason: str | None
    triggered_at: datetime


class DeviceClusterResponse(BaseModel):
    cluster_id: str
    center_latitude: float
    center_longitude: float
    device_count: int
    approximate_count: int
    precise_count: int
    moderate_count: int
    latest_captured_at: datetime | None
    device_ids: list[UUID] = Field(default_factory=list)


class IncidentRouteResponse(BaseModel):
    incident_id: UUID
    device_id: UUID
    started_at: datetime
    ended_at: datetime
    points: list[LocationEventPointResponse] = Field(default_factory=list)
    geofence_events: list[GeofenceEventResponse] = Field(default_factory=list)


class IncidentRemoteActionEvidenceResponse(BaseModel):
    remote_action_id: UUID
    action_kind: RemoteActionKind
    state: RemoteActionState
    reason: str
    requested_by_sub: str
    requested_at: datetime
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    acked_at: datetime | None = None
    failed_at: datetime | None = None
    last_error: str | None = None


class CaseEvidenceEntryResponse(BaseModel):
    entry_id: str
    kind: str
    title: str
    summary: str
    occurred_at: datetime
    actor_sub: str | None = None
    mutable: bool = False
    data: dict = Field(default_factory=dict)


class CaseEvidenceChainResponse(BaseModel):
    incident: IncidentResponse
    incident_summary: dict = Field(default_factory=dict)
    location_timeline: list[LocationEventPointResponse] = Field(default_factory=list)
    audit_trail: list[AuditLogResponse] = Field(default_factory=list)
    command_history: list[IncidentRemoteActionEvidenceResponse] = Field(default_factory=list)
    geofence_events: list[GeofenceEventResponse] = Field(default_factory=list)
    actions_taken: list[IncidentRemoteActionEvidenceResponse] = Field(default_factory=list)
    notes: list[IncidentNoteResponse] = Field(default_factory=list)
    attachments: list[IncidentAttachmentResponse] = Field(default_factory=list)
    exports: list[IncidentEvidenceExportResponse] = Field(default_factory=list)
    external_shares: list[EvidenceShareResponse] = Field(default_factory=list)
    entries: list[CaseEvidenceEntryResponse] = Field(default_factory=list)


class RemoteActionCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    incident_id: UUID | None = None
    action_kind: RemoteActionKind
    reason: str = Field(min_length=2, max_length=250)
    delayed_until: datetime | None = None
    elevated_confirmation: bool = False
    acknowledge_wipe_tradeoff: bool = False


class RemoteActionResponse(BaseModel):
    remote_action_id: UUID
    org_id: UUID
    device_id: UUID
    incident_id: UUID | None
    action_kind: RemoteActionKind
    state: str
    delayed_until: datetime | None
    approval_request_id: UUID | None = None
    policy_reason: str | None = None
    requested_at: datetime


class PolicyDecisionResponse(BaseModel):
    action_type: PolicyActionType
    allowed: bool
    requires_approval: bool
    reason_code: str
    reason: str
    required_approvals: int = 0
    owner_subject: str | None = None
    incident_state: IncidentCaseState | None = None


class ApprovalDecisionRequest(BaseModel):
    approve: bool
    reason: str = Field(min_length=4, max_length=280)


class ApprovalDecisionEntryResponse(BaseModel):
    approval_decision_id: UUID
    actor_sub: str
    decision: str
    reason: str
    created_at: datetime


class SensitiveActionApprovalResponse(BaseModel):
    approval_id: UUID
    org_id: UUID
    action_type: PolicyActionType
    status: ApprovalStatus
    entity_type: str
    entity_id: str
    device_id: UUID | None = None
    incident_id: UUID | None = None
    requested_by_sub: str
    request_reason: str
    required_approvals: int
    approval_count: int
    policy_context: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    decisions: list[ApprovalDecisionEntryResponse] = Field(default_factory=list)


class AuditLogResponse(BaseModel):
    audit_id: UUID
    org_id: UUID | None
    actor_sub: str
    action: str
    entity_type: str
    entity_id: str
    metadata: dict
    occurred_at: datetime
    previous_hash: str | None
    event_hash: str


class ObservabilityAlertResponse(BaseModel):
    code: str
    severity: str
    actor_sub: str | None = None
    count: int
    summary: str
    device_count: int | None = None
    examples: list[str] = Field(default_factory=list)


class IngestionHealthPanel(BaseModel):
    window_hours: int
    location_events: int
    last_ingested_at: datetime | None = None
    approximate_events: int
    telemetry_verified_events: int


class FailedCommandsPanel(BaseModel):
    failed_count: int
    expired_count: int
    top_last_errors: list[tuple[str, int]] = Field(default_factory=list)


class BatteryImpactPanel(BaseModel):
    samples_with_battery: int
    average_battery_percent: float | None = None
    low_battery_samples: int


class ConfidenceDistributionPanel(BaseModel):
    confidence_buckets: dict[str, int] = Field(default_factory=dict)
    precision_distribution: dict[str, int] = Field(default_factory=dict)


class SuspiciousActorPanel(BaseModel):
    top_lookup_actor: dict | None = None
    unique_lookup_actors: int


class ObservabilityDashboardResponse(BaseModel):
    ingestion_health: IngestionHealthPanel
    failed_commands: FailedCommandsPanel
    battery_impact: BatteryImpactPanel
    location_confidence_distribution: ConfidenceDistributionPanel
    suspicious_actor_behavior: SuspiciousActorPanel


class AccessReviewReportResponse(BaseModel):
    window_hours: int
    totals: dict[str, int] = Field(default_factory=dict)
    reviews: list[dict] = Field(default_factory=list)


class AuditReportEntryResponse(BaseModel):
    audit_id: str
    occurred_at: datetime
    actor_sub: str
    action: str
    entity_type: str
    entity_id: str
    reason: str | None = None
    result: str | None = None
    request_id: str | None = None
    device_id: str | None = None
    privacy_preserving: bool = True
    metadata: dict = Field(default_factory=dict)


class AuditReportResponse(BaseModel):
    org_id: UUID
    window_hours: int
    generated_at: datetime
    entries: list[AuditReportEntryResponse] = Field(default_factory=list)


class AuditLogChainVerificationResponse(BaseModel):
    org_id: UUID
    verified: bool
    checked_events: int
    broken_at_audit_id: UUID | None = None
    reason: str | None = None


class NotificationCreateRequest(BaseModel):
    org_id: UUID
    incident_id: UUID | None = None
    device_id: UUID | None = None
    remote_action_id: UUID | None = None
    recipient_sub: str | None = Field(default=None, max_length=150)
    recipient_token: str | None = Field(default=None, max_length=255)
    channel: str = Field(min_length=2, max_length=32)
    template: str = Field(min_length=2, max_length=80)
    payload: dict = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    notification_event_id: UUID
    status: str
    created_at: datetime


class IpEnrichmentRequest(BaseModel):
    ip_address: str = Field(min_length=3, max_length=64)


class IpEnrichmentResponse(BaseModel):
    ip_address: str
    is_approximate: bool
    country: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    accuracy_km: float | None


class RuleEvaluationResponse(BaseModel):
    rules: list[str] = Field(default_factory=list)
