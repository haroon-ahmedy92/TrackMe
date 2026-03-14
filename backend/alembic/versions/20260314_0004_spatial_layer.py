"""add geofence events for spatial layer

Revision ID: 20260314_0004
Revises: 20260314_0003
Create Date: 2026-03-14 17:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260314_0004'
down_revision = '20260314_0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    geofence_event_type = postgresql.ENUM('enter', 'exit', name='geofenceeventtype')
    geofence_event_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'geofence_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('geofence_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('geofences.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('location_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('location_events.id'), nullable=False),
        sa.Column('event_type', geofence_event_type, nullable=False),
        sa.Column('precision', postgresql.ENUM(name='locationprecision', create_type=False), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('alert_emitted', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('suppressed_reason', sa.String(length=80), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_geofence_events_org_triggered', 'geofence_events', ['org_id', 'triggered_at'])
    op.create_index('ix_geofence_events_device_triggered', 'geofence_events', ['device_id', 'triggered_at'])
    op.create_index('ix_geofence_events_geofence_triggered', 'geofence_events', ['geofence_id', 'triggered_at'])


def downgrade() -> None:
    op.drop_index('ix_geofence_events_geofence_triggered', table_name='geofence_events')
    op.drop_index('ix_geofence_events_device_triggered', table_name='geofence_events')
    op.drop_index('ix_geofence_events_org_triggered', table_name='geofence_events')
    op.drop_table('geofence_events')
    postgresql.ENUM(name='geofenceeventtype').drop(op.get_bind(), checkfirst=True)
