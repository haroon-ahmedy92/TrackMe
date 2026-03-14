from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import GeofenceEventType, IncidentCaseState, LocationPrecision, RemoteActionKind, UserRole
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
    rotate_existing_active: bool = True


class DeviceKeyResponse(BaseModel):
    key_record_id: UUID
    org_id: UUID
    device_id: UUID
    key_id: str
    algorithm: str
    created_at: datetime


class DeviceKeyRotateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    key_id: str = Field(min_length=2, max_length=80)
    public_key_pem: str = Field(min_length=16)
    algorithm: str = Field(min_length=3, max_length=32)


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
    telemetry_signature: str | None = None
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
    ip_is_approximate: bool
    rule_matches: list[str] = Field(default_factory=list)
    suspicious_alerts: list[str] = Field(default_factory=list)


class IncidentCreateRequest(BaseModel):
    org_id: UUID
    device_id: UUID
    ticket_reference: str = Field(min_length=2, max_length=80)
    recovery_message: str = Field(min_length=2, max_length=280)
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
    recovery_message: str | None
    lost_mode_until: datetime | None
    wipe_scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime


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
    latitude: float | None
    longitude: float | None
    accuracy_meters: float | None
    precision: LocationPrecision
    confidence_score: int | None
    source_methods: list[str] = Field(default_factory=list)
    is_ip_approximate: bool
    source_label: str


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
    requested_at: datetime


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
