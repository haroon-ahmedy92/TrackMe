"""init platform schema with postgis

Revision ID: 20260310_0001
Revises: None
Create Date: 2026-03-10 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260310_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    user_role = postgresql.ENUM('owner', 'admin', 'security', name='userrole')
    enrollment_status = postgresql.ENUM('active', 'revoked', name='enrollmentstatus')
    checkin_mode = postgresql.ENUM('normal', 'lost_mode', name='checkinmode')
    location_precision = postgresql.ENUM('precise', 'moderate', 'approximate', name='locationprecision')
    incident_state = postgresql.ENUM(
        'normal',
        'suspected_lost',
        'confirmed_stolen',
        'recovered',
        'wiped',
        'decommissioned',
        name='incidentcasestate',
    )
    remote_action_kind = postgresql.ENUM('lock', 'wipe', name='remoteactionkind')
    remote_action_state = postgresql.ENUM('requested', 'dispatched', 'applied', 'failed', 'cancelled', name='remoteactionstate')
    notification_status = postgresql.ENUM('queued', 'sent', 'failed', name='notificationstatus')
    enrollment_type = postgresql.ENUM('owner_enrolled', 'org_managed', name='enrollmenttype')

    bind = op.get_bind()
    for enum_type in (
        user_role,
        enrollment_status,
        checkin_mode,
        location_precision,
        incident_state,
        remote_action_kind,
        remote_action_state,
        notification_status,
        enrollment_type,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        'orgs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False, unique=True),
        sa.Column('name', sa.String(length=180), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('subject', sa.String(length=150), nullable=False),
        sa.Column('display_name', sa.String(length=140), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('role', user_role, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('org_id', 'subject', name='uq_users_org_subject'),
    )

    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=True),
        sa.Column('alias', sa.String(length=120), nullable=False),
        sa.Column('enrollment_type', enrollment_type, nullable=False),
        sa.Column('is_policy_managed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('consent_version', sa.String(length=40), nullable=False),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_devices_org_enrolled', 'devices', ['organization_id', 'enrolled_at'])

    op.create_table(
        'enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('status', enrollment_status, nullable=False),
        sa.Column('consent_version', sa.String(length=40), nullable=False),
        sa.Column('enrolled_by_sub', sa.String(length=150), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_enrollments_org_device_created', 'enrollments', ['org_id', 'device_id', 'created_at'])

    op.create_table(
        'device_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('key_id', sa.String(length=80), nullable=False),
        sa.Column('public_key_pem', sa.Text(), nullable=False),
        sa.Column('algorithm', sa.String(length=32), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('device_id', 'key_id', name='uq_device_keys_device_key'),
    )

    op.create_table(
        'location_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('idempotency_key', sa.String(length=120), nullable=False),
        sa.Column('mode', checkin_mode, nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('accuracy_meters', sa.Numeric(8, 2), nullable=True),
        sa.Column('precision', location_precision, nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('source_methods', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('network_type', sa.String(length=24), nullable=True),
        sa.Column('battery_percent', sa.Integer(), nullable=True),
        sa.Column('motion_state', sa.String(length=24), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('ip_country', sa.String(length=64), nullable=True),
        sa.Column('ip_city', sa.String(length=120), nullable=True),
        sa.Column('ip_latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('ip_longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('ip_accuracy_km', sa.Numeric(8, 2), nullable=True),
        sa.Column('is_ip_approximate', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('telemetry_signature', sa.String(length=128), nullable=True),
        sa.Column('telemetry_key_id', sa.String(length=64), nullable=True),
        sa.Column('telemetry_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('integrity_verdict', sa.String(length=64), nullable=True),
        sa.Column('location_geom', postgresql.USER_DEFINED_TYPE(), nullable=True),
        sa.UniqueConstraint('device_id', 'idempotency_key', name='uq_location_events_device_idempotency'),
    )
    op.execute(
        "ALTER TABLE location_events ALTER COLUMN location_geom TYPE geometry(POINT,4326) USING location_geom::geometry"
    )
    op.create_index('ix_location_events_org_captured', 'location_events', ['org_id', 'captured_at'])
    op.create_index('ix_location_events_device_captured', 'location_events', ['device_id', 'captured_at'])
    op.execute('CREATE INDEX ix_location_events_geom_gist ON location_events USING GIST (location_geom)')

    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('ticket_reference', sa.String(length=80), nullable=False),
        sa.Column('state', incident_state, nullable=False),
        sa.Column('recovery_message', sa.String(length=280), nullable=True),
        sa.Column('elevated_confirmed_by', sa.String(length=150), nullable=True),
        sa.Column('lost_mode_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('wipe_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('wipe_reason', sa.String(length=250), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incidents_org_state_updated', 'incidents', ['org_id', 'state', 'updated_at'])

    op.create_table(
        'incident_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('state', incident_state, nullable=False),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('summary', sa.String(length=280), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incident_events_incident_occurred', 'incident_events', ['incident_id', 'occurred_at'])

    op.create_table(
        'geofences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('radius_meters', sa.Integer(), nullable=False),
        sa.Column('center_latitude', sa.Numeric(10, 7), nullable=False),
        sa.Column('center_longitude', sa.Numeric(10, 7), nullable=False),
        sa.Column('center_geom', postgresql.USER_DEFINED_TYPE(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("ALTER TABLE geofences ALTER COLUMN center_geom TYPE geometry(POINT,4326) USING center_geom::geometry")
    op.create_index('ix_geofences_org_enabled', 'geofences', ['org_id', 'is_enabled'])
    op.execute('CREATE INDEX ix_geofences_geom_gist ON geofences USING GIST (center_geom)')

    op.create_table(
        'remote_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=True),
        sa.Column('action_kind', remote_action_kind, nullable=False),
        sa.Column('state', remote_action_state, nullable=False),
        sa.Column('reason', sa.String(length=250), nullable=False),
        sa.Column('requires_elevated_confirmation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('delayed_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_remote_actions_org_requested', 'remote_actions', ['org_id', 'requested_at'])

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=True),
        sa.Column('actor_sub', sa.String(length=150), nullable=False),
        sa.Column('action', sa.String(length=120), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.String(length=120), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('previous_hash', sa.String(length=64), nullable=True),
        sa.Column('event_hash', sa.String(length=64), nullable=False),
    )
    op.create_index('ix_audit_logs_org_occurred', 'audit_logs', ['org_id', 'occurred_at'])

    op.create_table(
        'notification_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=True),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('recipient_sub', sa.String(length=150), nullable=True),
        sa.Column('channel', sa.String(length=32), nullable=False),
        sa.Column('template', sa.String(length=80), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', notification_status, nullable=False),
        sa.Column('provider_message_id', sa.String(length=150), nullable=True),
        sa.Column('error_message', sa.String(length=250), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_notification_events_org_created', 'notification_events', ['org_id', 'created_at'])


def downgrade() -> None:
    for name in (
        'notification_events',
        'audit_logs',
        'remote_actions',
        'geofences',
        'incident_events',
        'incidents',
        'location_events',
        'device_keys',
        'enrollments',
        'devices',
        'users',
        'orgs',
    ):
        op.drop_table(name)

    bind = op.get_bind()
    for enum_name in (
        'notificationstatus',
        'remoteactionstate',
        'remoteactionkind',
        'incidentcasestate',
        'locationprecision',
        'checkinmode',
        'enrollmentstatus',
        'userrole',
        'enrollmenttype',
    ):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
