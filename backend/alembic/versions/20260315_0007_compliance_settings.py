"""add compliance settings and deprovision tables

Revision ID: 20260315_0007
Revises: 20260314_0006
Create Date: 2026-03-15 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260315_0007'
down_revision = '20260314_0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    deprovision_status = postgresql.ENUM('requested', 'completed', name='deprovisionstatus')
    deprovision_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'tenant_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('location_event_days', sa.Integer(), nullable=False),
        sa.Column('audit_log_days', sa.Integer(), nullable=False),
        sa.Column('incident_evidence_days', sa.Integer(), nullable=False),
        sa.Column('updated_by_sub', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('org_id', name='uq_tenant_settings_org'),
    )

    op.create_table(
        'abuse_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('contact_email', sa.String(length=200), nullable=True),
        sa.Column('reported_by_sub', sa.String(length=150), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_abuse_reports_org_created', 'abuse_reports', ['org_id', 'created_at'])

    op.create_table(
        'deprovision_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('reason', sa.String(length=280), nullable=False),
        sa.Column('status', deprovision_status, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_deprovision_requests_org_created', 'deprovision_requests', ['org_id', 'created_at'])
    op.create_index('ix_deprovision_requests_device_status', 'deprovision_requests', ['device_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_deprovision_requests_device_status', table_name='deprovision_requests')
    op.drop_index('ix_deprovision_requests_org_created', table_name='deprovision_requests')
    op.drop_table('deprovision_requests')
    op.drop_index('ix_abuse_reports_org_created', table_name='abuse_reports')
    op.drop_table('abuse_reports')
    op.drop_table('tenant_settings')
    postgresql.ENUM(name='deprovisionstatus').drop(op.get_bind(), checkfirst=True)
