from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

try:
    from geoalchemy2 import Geometry
except ModuleNotFoundError:  # pragma: no cover
    # Lightweight fallback for environments without PostGIS deps installed.
    class Geometry(String):  # type: ignore[misc]
        def __init__(self, *args, **kwargs):
            super().__init__()


class EnrollmentType(str, enum.Enum):
    OWNER_ENROLLED = 'owner_enrolled'
    ORG_MANAGED = 'org_managed'


class CheckInMode(str, enum.Enum):
    NORMAL = 'normal'
    MISPLACED = 'misplaced'
    LOST_MODE = 'lost_mode'


class RemoteActionType(str, enum.Enum):
    LOCK = 'lock'
    WIPE = 'wipe'


class RemoteActionStatus(str, enum.Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


class IncidentState(str, enum.Enum):
    NORMAL = 'normal'
    SUSPECTED_LOST = 'suspected_lost'
    CONFIRMED_STOLEN = 'confirmed_stolen'
    RECOVERED = 'recovered'
    WIPED = 'wiped'
    DECOMMISSIONED = 'decommissioned'


class Device(Base):
    __tablename__ = 'devices'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=True)
    alias: Mapped[str] = mapped_column(String(120), nullable=False)
    enrollment_type: Mapped[EnrollmentType] = mapped_column(Enum(EnrollmentType), nullable=False)
    is_policy_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_trust_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    last_seen_trust_summary: Mapped[str | None] = mapped_column(String(280), nullable=True)
    last_seen_trust_reasons_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    last_seen_integrity_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_root_suspicion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_debug_suspicion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_mock_location_suspicion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_trust_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    telemetry_events: Mapped[list['TelemetryEvent']] = relationship(back_populates='device')
    incidents: Mapped[list['IncidentRecord']] = relationship(back_populates='device')
    location_events: Mapped[list['LocationEvent']] = relationship(back_populates='device')
    enrollments: Mapped[list['Enrollment']] = relationship(back_populates='device')
    geofences: Mapped[list['Geofence']] = relationship(back_populates='device')
    remote_actions: Mapped[list['RemoteAction']] = relationship(back_populates='device')
    push_tokens: Mapped[list['DevicePushToken']] = relationship(back_populates='device')
    ownership_bindings: Mapped[list['DeviceOwnershipBinding']] = relationship()
    access_policies: Mapped[list['DeviceAccessPolicy']] = relationship()
    pairing_tokens: Mapped[list['PairingToken']] = relationship()
    ownership_transfers: Mapped[list['OwnershipTransfer']] = relationship()
    access_reviews: Mapped[list['AccessReview']] = relationship()


class TelemetryEvent(Base):
    __tablename__ = 'telemetry_events'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    mode: Mapped[CheckInMode] = mapped_column(Enum(CheckInMode), nullable=False)
    checkin_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    battery_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)

    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    accuracy_meters: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    method_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_approximate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    location_geom: Mapped[str | None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    telemetry_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telemetry_algorithm: Mapped[str | None] = mapped_column(String(32), nullable=True)
    telemetry_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telemetry_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telemetry_verification_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    integrity_token: Mapped[str | None] = mapped_column(Text, nullable=True)

    device: Mapped[Device] = relationship(back_populates='telemetry_events')


class AuditEvent(Base):
    __tablename__ = 'audit_events'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class RemoteActionRequest(Base):
    __tablename__ = 'remote_action_requests'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('incident_records.id'), nullable=True)
    action_type: Mapped[RemoteActionType] = mapped_column(Enum(RemoteActionType), nullable=False)
    status: Mapped[RemoteActionStatus] = mapped_column(Enum(RemoteActionStatus), nullable=False)
    ticket_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(250), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IncidentRecord(Base):
    __tablename__ = 'incident_records'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    ticket_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[IncidentState] = mapped_column(Enum(IncidentState), nullable=False, default=IncidentState.SUSPECTED_LOST)
    recovery_message: Mapped[str] = mapped_column(String(280), nullable=False)
    elevated_confirmed_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    wipe_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wipe_reason: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device: Mapped['Device'] = relationship(back_populates='incidents')
    timeline_events: Mapped[list['IncidentTimelineEvent']] = relationship(back_populates='incident')


class IncidentTimelineEvent(Base):
    __tablename__ = 'incident_timeline_events'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incident_records.id'), nullable=False)
    state: Mapped[IncidentState] = mapped_column(Enum(IncidentState), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(String(280), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incident: Mapped['IncidentRecord'] = relationship(back_populates='timeline_events')


class UserRole(str, enum.Enum):
    OWNER = 'owner'
    ADMIN = 'admin'
    SECURITY = 'security'
    SECURITY_OPERATOR = 'security_operator'


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = 'active'
    REVOKED = 'revoked'


class OwnershipType(str, enum.Enum):
    SINGLE_USER = 'single_user'
    ORGANIZATION_OWNED = 'organization_owned'


class OwnershipProofKind(str, enum.Enum):
    ENROLLMENT_TOKEN = 'enrollment_token'
    QR_CODE = 'qr_code'
    ADMIN_APPROVAL = 'admin_approval'
    TRANSFER_APPROVAL = 'transfer_approval'
    MANUAL_REVIEW = 'manual_review'


class AccessReviewStatus(str, enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'


class OwnershipTransferStatus(str, enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'


class LocationPrecision(str, enum.Enum):
    PRECISE = 'precise'
    MODERATE = 'moderate'
    APPROXIMATE = 'approximate'


class IncidentCaseState(str, enum.Enum):
    NORMAL = 'normal'
    SUSPECTED_LOST = 'suspected_lost'
    CONFIRMED_STOLEN = 'confirmed_stolen'
    RECOVERED = 'recovered'
    WIPED = 'wiped'
    DECOMMISSIONED = 'decommissioned'


class RemoteActionKind(str, enum.Enum):
    ENTER_LOST_MODE = 'enter_lost_mode'
    DISPLAY_RECOVERY_MESSAGE = 'display_recovery_message'
    LOCK = 'lock'
    WIPE = 'wipe'


class RemoteActionState(str, enum.Enum):
    PENDING_APPROVAL = 'pending_approval'
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    ACKED = 'acked'
    FAILED = 'failed'
    EXPIRED = 'expired'


class NotificationStatus(str, enum.Enum):
    QUEUED = 'queued'
    SENT = 'sent'
    FAILED = 'failed'


class QueuedEventStatus(str, enum.Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class DeprovisionStatus(str, enum.Enum):
    REQUESTED = 'requested'
    COMPLETED = 'completed'


class GeofenceEventType(str, enum.Enum):
    ENTER = 'enter'
    EXIT = 'exit'


class EvidenceExportFormat(str, enum.Enum):
    JSON = 'json'
    PDF = 'pdf'


class EvidenceExportStatus(str, enum.Enum):
    PENDING_APPROVAL = 'pending_approval'
    GENERATED = 'generated'
    FAILED = 'failed'


class PolicyActionType(str, enum.Enum):
    LOCATE = 'locate'
    ENTER_LOST_MODE = 'enter_lost_mode'
    DISPLAY_RECOVERY_MESSAGE = 'display_recovery_message'
    LOCK = 'lock'
    WIPE = 'wipe'
    EVIDENCE_EXPORT = 'evidence_export'
    RETENTION_UPDATE = 'retention_update'


class ApprovalStatus(str, enum.Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED = 'expired'


class ApprovalDecisionType(str, enum.Enum):
    APPROVE = 'approve'
    REJECT = 'reject'


class Organization(Base):
    __tablename__ = 'orgs'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    users: Mapped[list['User']] = relationship(back_populates='organization')
    devices: Mapped[list['Device']] = relationship()
    ownership_bindings: Mapped[list['DeviceOwnershipBinding']] = relationship()
    access_policies: Mapped[list['DeviceAccessPolicy']] = relationship()
    pairing_tokens: Mapped[list['PairingToken']] = relationship()
    ownership_transfers: Mapped[list['OwnershipTransfer']] = relationship()
    access_reviews: Mapped[list['AccessReview']] = relationship()
    sensitive_action_approvals: Mapped[list['SensitiveActionApproval']] = relationship()
    tenant_settings: Mapped[list['TenantSettings']] = relationship()
    abuse_reports: Mapped[list['AbuseReport']] = relationship()
    deprovision_requests: Mapped[list['DeprovisionRequest']] = relationship()


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('org_id', 'subject', name='uq_users_org_subject'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    subject: Mapped[str] = mapped_column(String(150), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(140), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    organization: Mapped['Organization'] = relationship(back_populates='users')
    owned_device_bindings: Mapped[list['DeviceOwnershipBinding']] = relationship(foreign_keys='DeviceOwnershipBinding.owner_user_id')


class Enrollment(Base):
    __tablename__ = 'enrollments'
    __table_args__ = (
        Index('ix_enrollments_org_device_created', 'org_id', 'device_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    status: Mapped[EnrollmentStatus] = mapped_column(Enum(EnrollmentStatus), nullable=False, default=EnrollmentStatus.ACTIVE)
    consent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    enrolled_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped['Device'] = relationship(back_populates='enrollments')


class DeviceKey(Base):
    __tablename__ = 'device_keys'
    __table_args__ = (
        UniqueConstraint('device_id', 'key_id', name='uq_device_keys_device_key'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    key_id: Mapped[str] = mapped_column(String(80), nullable=False)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_hardware_backed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attestation_format: Mapped[str | None] = mapped_column(String(48), nullable=True)
    attestation_record: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(280), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceOwnershipBinding(Base):
    __tablename__ = 'device_ownership_bindings'
    __table_args__ = (
        Index('ix_device_ownership_bindings_org_device_active', 'org_id', 'device_id', 'is_active'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    ownership_type: Mapped[OwnershipType] = mapped_column(Enum(OwnershipType), nullable=False)
    proof_kind: Mapped[OwnershipProofKind] = mapped_column(Enum(OwnershipProofKind), nullable=False)
    proof_reference: Mapped[str | None] = mapped_column(String(180), nullable=True)
    consent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    consent_captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bound_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeviceAccessPolicy(Base):
    __tablename__ = 'device_access_policies'
    __table_args__ = (
        UniqueConstraint('device_id', name='uq_device_access_policies_device'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    owner_can_locate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    admin_can_locate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    security_operator_can_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_access_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_can_export_evidence: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_can_export_evidence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    security_can_export_evidence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    admin_can_lock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    admin_can_wipe: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_incident_for_locate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    require_two_person_wipe_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PairingToken(Base):
    __tablename__ = 'pairing_tokens'
    __table_args__ = (
        UniqueConstraint('token_hash', name='uq_pairing_tokens_hash'),
        Index('ix_pairing_tokens_org_expires', 'org_id', 'expires_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    enrollment_type: Mapped[EnrollmentType] = mapped_column(Enum(EnrollmentType), nullable=False)
    ownership_type: Mapped[OwnershipType] = mapped_column(Enum(OwnershipType), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hint: Mapped[str] = mapped_column(String(16), nullable=False)
    issued_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    proof_kind: Mapped[OwnershipProofKind] = mapped_column(Enum(OwnershipProofKind), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OwnershipTransfer(Base):
    __tablename__ = 'ownership_transfers'
    __table_args__ = (
        Index('ix_ownership_transfers_org_device_created', 'org_id', 'device_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    from_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    to_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    approved_by_sub: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[OwnershipTransferStatus] = mapped_column(Enum(OwnershipTransferStatus), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AccessReview(Base):
    __tablename__ = 'access_reviews'
    __table_args__ = (
        Index('ix_access_reviews_org_device_created', 'org_id', 'device_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    reviewed_by_sub: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[AccessReviewStatus] = mapped_column(Enum(AccessReviewStatus), nullable=False)
    rationale: Mapped[str] = mapped_column(String(280), nullable=False)
    review_notes: Mapped[str | None] = mapped_column(String(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LocationEvent(Base):
    __tablename__ = 'location_events'
    __table_args__ = (
        UniqueConstraint('device_id', 'idempotency_key', name='uq_location_events_device_idempotency'),
        Index('ix_location_events_org_captured', 'org_id', 'captured_at'),
        Index('ix_location_events_device_captured', 'device_id', 'captured_at'),
        Index('ix_location_events_geom_gist', 'location_geom', postgresql_using='gist'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[CheckInMode] = mapped_column(Enum(CheckInMode), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    accuracy_meters: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    precision: Mapped[LocationPrecision] = mapped_column(Enum(LocationPrecision), nullable=False)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_methods: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    network_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    battery_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    motion_state: Mapped[str | None] = mapped_column(String(24), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ip_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    ip_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    ip_accuracy_km: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    is_ip_approximate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telemetry_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telemetry_algorithm: Mapped[str | None] = mapped_column(String(40), nullable=True)
    telemetry_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telemetry_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    telemetry_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    telemetry_verification_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    integrity_verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trust_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    trust_summary: Mapped[str | None] = mapped_column(String(280), nullable=True)
    trust_signals_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    location_geom: Mapped[str | None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)

    device: Mapped['Device'] = relationship(back_populates='location_events')


class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = (
        Index('ix_incidents_org_state_updated', 'org_id', 'state', 'updated_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    ticket_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[IncidentCaseState] = mapped_column(Enum(IncidentCaseState), nullable=False)
    recovery_message: Mapped[str | None] = mapped_column(String(280), nullable=True)
    elevated_confirmed_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    lost_mode_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wipe_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    wipe_reason: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    events: Mapped[list['IncidentEvent']] = relationship(back_populates='incident')
    notes: Mapped[list['IncidentNote']] = relationship(back_populates='incident')
    attachments: Mapped[list['IncidentAttachment']] = relationship(back_populates='incident')
    evidence_exports: Mapped[list['EvidenceExport']] = relationship(back_populates='incident')


class IncidentEvent(Base):
    __tablename__ = 'incident_events'
    __table_args__ = (
        Index('ix_incident_events_incident_occurred', 'incident_id', 'occurred_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=False)
    state: Mapped[IncidentCaseState] = mapped_column(Enum(IncidentCaseState), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(String(280), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incident: Mapped['Incident'] = relationship(back_populates='events')


class IncidentNote(Base):
    __tablename__ = 'incident_notes'
    __table_args__ = (
        Index('ix_incident_notes_incident_updated', 'incident_id', 'updated_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=False)
    author_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incident: Mapped['Incident'] = relationship(back_populates='notes')


class IncidentAttachment(Base):
    __tablename__ = 'incident_attachments'
    __table_args__ = (
        Index('ix_incident_attachments_incident_created', 'incident_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=False)
    uploaded_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    file_name: Mapped[str] = mapped_column(String(180), nullable=False)
    media_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(220), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    incident: Mapped['Incident'] = relationship(back_populates='attachments')


class EvidenceExport(Base):
    __tablename__ = 'evidence_exports'
    __table_args__ = (
        Index('ix_evidence_exports_incident_created', 'incident_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=False)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    format: Mapped[EvidenceExportFormat] = mapped_column(Enum(EvidenceExportFormat), nullable=False)
    status: Mapped[EvidenceExportStatus] = mapped_column(Enum(EvidenceExportStatus), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    redact_fields_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped['Incident'] = relationship(back_populates='evidence_exports')


class SensitiveActionApproval(Base):
    __tablename__ = 'sensitive_action_approvals'
    __table_args__ = (
        Index('ix_sensitive_action_approvals_org_status_created', 'org_id', 'status', 'created_at'),
        Index('ix_sensitive_action_approvals_entity', 'entity_type', 'entity_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    action_type: Mapped[PolicyActionType] = mapped_column(Enum(PolicyActionType), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=True)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    request_reason: Mapped[str] = mapped_column(String(280), nullable=False)
    required_approvals: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    policy_context_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    requested_payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    decisions: Mapped[list['SensitiveActionApprovalDecision']] = relationship(back_populates='approval')


class SensitiveActionApprovalDecision(Base):
    __tablename__ = 'sensitive_action_approval_decisions'
    __table_args__ = (
        UniqueConstraint('approval_id', 'actor_sub', name='uq_sensitive_action_approval_actor'),
        Index('ix_sensitive_action_approval_decisions_approval_created', 'approval_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('sensitive_action_approvals.id'), nullable=False)
    actor_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    decision: Mapped[ApprovalDecisionType] = mapped_column(Enum(ApprovalDecisionType), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    approval: Mapped['SensitiveActionApproval'] = relationship(back_populates='decisions')


class Geofence(Base):
    __tablename__ = 'geofences'
    __table_args__ = (
        Index('ix_geofences_org_enabled', 'org_id', 'is_enabled'),
        Index('ix_geofences_geom_gist', 'center_geom', postgresql_using='gist'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    radius_meters: Mapped[int] = mapped_column(Integer, nullable=False)
    center_latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    center_longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    center_geom: Mapped[str | None] = mapped_column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device: Mapped['Device | None'] = relationship(back_populates='geofences')


class GeofenceEvent(Base):
    __tablename__ = 'geofence_events'
    __table_args__ = (
        Index('ix_geofence_events_org_triggered', 'org_id', 'triggered_at'),
        Index('ix_geofence_events_device_triggered', 'device_id', 'triggered_at'),
        Index('ix_geofence_events_geofence_triggered', 'geofence_id', 'triggered_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    geofence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('geofences.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    location_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('location_events.id'), nullable=False)
    event_type: Mapped[GeofenceEventType] = mapped_column(Enum(GeofenceEventType), nullable=False)
    precision: Mapped[LocationPrecision] = mapped_column(Enum(LocationPrecision), nullable=False)
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    alert_emitted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    suppressed_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RemoteAction(Base):
    __tablename__ = 'remote_actions'
    __table_args__ = (
        Index('ix_remote_actions_org_requested', 'org_id', 'requested_at'),
        Index('ix_remote_actions_device_state', 'device_id', 'state'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=True)
    action_kind: Mapped[RemoteActionKind] = mapped_column(Enum(RemoteActionKind), nullable=False)
    state: Mapped[RemoteActionState] = mapped_column(Enum(RemoteActionState), nullable=False)
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    command_payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    command_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    signature_algorithm: Mapped[str] = mapped_column(String(40), nullable=False)
    requires_elevated_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delayed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(250), nullable=True)
    acknowledgement_metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device: Mapped['Device'] = relationship(back_populates='remote_actions')


class DevicePushToken(Base):
    __tablename__ = 'device_push_tokens'
    __table_args__ = (
        Index('ix_device_push_tokens_org_device_active', 'org_id', 'device_id', 'is_active'),
        UniqueConstraint('push_token', name='uq_device_push_tokens_token'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    key_id: Mapped[str] = mapped_column(String(80), nullable=False)
    push_token: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(24), nullable=False, default='android')
    app_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped['Device'] = relationship(back_populates='push_tokens')


class TenantSettings(Base):
    __tablename__ = 'tenant_settings'
    __table_args__ = (
        UniqueConstraint('org_id', name='uq_tenant_settings_org'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    location_event_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    audit_log_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    incident_evidence_days: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    locate_reason_min_length: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    require_incident_for_locate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lock_requires_active_incident: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wipe_requires_policy_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    wipe_requires_confirmed_stolen: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    high_risk_actions_require_two_person: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evidence_export_requires_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_sub: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AbuseReport(Base):
    __tablename__ = 'abuse_reports'
    __table_args__ = (
        Index('ix_abuse_reports_org_created', 'org_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reported_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='submitted')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeprovisionRequest(Base):
    __tablename__ = 'deprovision_requests'
    __table_args__ = (
        Index('ix_deprovision_requests_org_created', 'org_id', 'created_at'),
        Index('ix_deprovision_requests_device_status', 'device_id', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    reason: Mapped[str] = mapped_column(String(280), nullable=False)
    status: Mapped[DeprovisionStatus] = mapped_column(Enum(DeprovisionStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    __table_args__ = (
        Index('ix_audit_logs_org_occurred', 'org_id', 'occurred_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=True)
    actor_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class NotificationEvent(Base):
    __tablename__ = 'notification_events'
    __table_args__ = (
        Index('ix_notification_events_org_created', 'org_id', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=True)
    remote_action_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('remote_actions.id'), nullable=True)
    recipient_sub: Mapped[str | None] = mapped_column(String(150), nullable=True)
    recipient_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    template: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EventQueueItem(Base):
    __tablename__ = 'event_queue_items'
    __table_args__ = (
        UniqueConstraint('idempotency_key', name='uq_event_queue_items_idempotency'),
        Index('ix_event_queue_items_status_available', 'status', 'available_at'),
        Index('ix_event_queue_items_topic_created', 'topic', 'created_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=True)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(120), nullable=False)
    producer: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    headers_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[QueuedEventStatus] = mapped_column(Enum(QueuedEventStatus), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuleExecutionLock(Base):
    __tablename__ = 'rule_execution_locks'
    __table_args__ = (
        UniqueConstraint('org_id', 'rule_code', 'scope_key', name='uq_rule_execution_locks_scope'),
        Index('ix_rule_execution_locks_cooldown', 'cooldown_until'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=True)
    rule_code: Mapped[str] = mapped_column(String(120), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(180), nullable=False)
    last_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('event_queue_items.id'), nullable=True)
    last_triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cooldown_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
