"""add policy engine settings and sensitive action approvals

Revision ID: 20260319_0010
Revises: 20260317_0009
Create Date: 2026-03-19 10:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260319_0010'
down_revision = '20260317_0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'pending_approval'")
    op.execute("ALTER TYPE evidenceexportstatus ADD VALUE IF NOT EXISTS 'pending_approval'")

    policy_action_type = postgresql.ENUM(
        'locate',
        'enter_lost_mode',
        'display_recovery_message',
        'lock',
        'wipe',
        'evidence_export',
        'retention_update',
        name='policyactiontype',
    )
    approval_status = postgresql.ENUM('pending', 'approved', 'rejected', 'expired', name='approvalstatus')
    approval_decision_type = postgresql.ENUM('approve', 'reject', name='approvaldecisiontype')

    policy_action_type.create(op.get_bind(), checkfirst=True)
    approval_status.create(op.get_bind(), checkfirst=True)
    approval_decision_type.create(op.get_bind(), checkfirst=True)

    op.add_column('device_access_policies', sa.Column('owner_can_export_evidence', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('device_access_policies', sa.Column('admin_can_export_evidence', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('device_access_policies', sa.Column('security_can_export_evidence', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('device_access_policies', sa.Column('admin_can_lock', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('device_access_policies', sa.Column('admin_can_wipe', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('device_access_policies', sa.Column('require_incident_for_locate', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('device_access_policies', sa.Column('require_two_person_wipe_approval', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.add_column('tenant_settings', sa.Column('locate_reason_min_length', sa.Integer(), nullable=False, server_default='8'))
    op.add_column('tenant_settings', sa.Column('require_incident_for_locate', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('tenant_settings', sa.Column('lock_requires_active_incident', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('tenant_settings', sa.Column('wipe_requires_policy_approval', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('tenant_settings', sa.Column('wipe_requires_confirmed_stolen', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('tenant_settings', sa.Column('high_risk_actions_require_two_person', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('tenant_settings', sa.Column('evidence_export_requires_permission', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'sensitive_action_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('action_type', policy_action_type, nullable=False),
        sa.Column('status', approval_status, nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.String(length=120), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=True),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('request_reason', sa.String(length=280), nullable=False),
        sa.Column('required_approvals', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('policy_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('requested_payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        'ix_sensitive_action_approvals_org_status_created',
        'sensitive_action_approvals',
        ['org_id', 'status', 'created_at'],
    )
    op.create_index(
        'ix_sensitive_action_approvals_entity',
        'sensitive_action_approvals',
        ['entity_type', 'entity_id'],
    )

    op.create_table(
        'sensitive_action_approval_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('approval_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sensitive_action_approvals.id'), nullable=False),
        sa.Column('actor_sub', sa.String(length=150), nullable=False),
        sa.Column('decision', approval_decision_type, nullable=False),
        sa.Column('reason', sa.String(length=280), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('approval_id', 'actor_sub', name='uq_sensitive_action_approval_actor'),
    )
    op.create_index(
        'ix_sensitive_action_approval_decisions_approval_created',
        'sensitive_action_approval_decisions',
        ['approval_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_sensitive_action_approval_decisions_approval_created', table_name='sensitive_action_approval_decisions')
    op.drop_table('sensitive_action_approval_decisions')
    op.drop_index('ix_sensitive_action_approvals_entity', table_name='sensitive_action_approvals')
    op.drop_index('ix_sensitive_action_approvals_org_status_created', table_name='sensitive_action_approvals')
    op.drop_table('sensitive_action_approvals')

    op.drop_column('tenant_settings', 'evidence_export_requires_permission')
    op.drop_column('tenant_settings', 'high_risk_actions_require_two_person')
    op.drop_column('tenant_settings', 'wipe_requires_confirmed_stolen')
    op.drop_column('tenant_settings', 'wipe_requires_policy_approval')
    op.drop_column('tenant_settings', 'lock_requires_active_incident')
    op.drop_column('tenant_settings', 'require_incident_for_locate')
    op.drop_column('tenant_settings', 'locate_reason_min_length')

    op.drop_column('device_access_policies', 'require_two_person_wipe_approval')
    op.drop_column('device_access_policies', 'require_incident_for_locate')
    op.drop_column('device_access_policies', 'admin_can_wipe')
    op.drop_column('device_access_policies', 'admin_can_lock')
    op.drop_column('device_access_policies', 'security_can_export_evidence')
    op.drop_column('device_access_policies', 'admin_can_export_evidence')
    op.drop_column('device_access_policies', 'owner_can_export_evidence')

    postgresql.ENUM(name='approvaldecisiontype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='approvalstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='policyactiontype').drop(op.get_bind(), checkfirst=True)
