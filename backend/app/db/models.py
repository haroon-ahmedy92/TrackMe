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

    telemetry_events: Mapped[list['TelemetryEvent']] = relationship(back_populates='device')
    incidents: Mapped[list['IncidentRecord']] = relationship(back_populates='device')
    location_events: Mapped[list['LocationEvent']] = relationship(back_populates='device')
    enrollments: Mapped[list['Enrollment']] = relationship(back_populates='device')
    geofences: Mapped[list['Geofence']] = relationship(back_populates='device')
    remote_actions: Mapped[list['RemoteAction']] = relationship(back_populates='device')


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


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = 'active'
    REVOKED = 'revoked'


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
    LOCK = 'lock'
    WIPE = 'wipe'


class RemoteActionState(str, enum.Enum):
    REQUESTED = 'requested'
    DISPATCHED = 'dispatched'
    APPLIED = 'applied'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class NotificationStatus(str, enum.Enum):
    QUEUED = 'queued'
    SENT = 'sent'
    FAILED = 'failed'


class Organization(Base):
    __tablename__ = 'orgs'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    users: Mapped[list['User']] = relationship(back_populates='organization')
    devices: Mapped[list['Device']] = relationship()


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
    telemetry_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telemetry_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    integrity_verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class RemoteAction(Base):
    __tablename__ = 'remote_actions'
    __table_args__ = (
        Index('ix_remote_actions_org_requested', 'org_id', 'requested_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('orgs.id'), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('devices.id'), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('incidents.id'), nullable=True)
    action_kind: Mapped[RemoteActionKind] = mapped_column(Enum(RemoteActionKind), nullable=False)
    state: Mapped[RemoteActionState] = mapped_column(Enum(RemoteActionState), nullable=False)
    reason: Mapped[str] = mapped_column(String(250), nullable=False)
    requires_elevated_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delayed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by_sub: Mapped[str] = mapped_column(String(150), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device: Mapped['Device'] = relationship(back_populates='remote_actions')


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
    recipient_sub: Mapped[str | None] = mapped_column(String(150), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    template: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(250), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
