"""add command delivery queue and push tokens

Revision ID: 20260314_0003
Revises: 20260313_0002_enrollment_rbac
Create Date: 2026-03-14 10:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260314_0003'
down_revision = '20260313_0002_enrollment_rbac'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE remoteactionkind ADD VALUE IF NOT EXISTS 'enter_lost_mode'")
    op.execute("ALTER TYPE remoteactionkind ADD VALUE IF NOT EXISTS 'display_recovery_message'")
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'pending'")
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'sent'")
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'delivered'")
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'acked'")
    op.execute("ALTER TYPE remoteactionstate ADD VALUE IF NOT EXISTS 'expired'")

    op.add_column('remote_actions', sa.Column('command_payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))
    op.add_column('remote_actions', sa.Column('command_signature', sa.String(length=128), nullable=True, server_default=''))
    op.add_column('remote_actions', sa.Column('signature_algorithm', sa.String(length=40), nullable=True, server_default='HMAC_SHA256_PLACEHOLDER'))
    op.add_column('remote_actions', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remote_actions', sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remote_actions', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remote_actions', sa.Column('acked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remote_actions', sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('remote_actions', sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('remote_actions', sa.Column('last_error', sa.String(length=250), nullable=True))
    op.add_column('remote_actions', sa.Column('acknowledgement_metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))
    op.create_index('ix_remote_actions_device_state', 'remote_actions', ['device_id', 'state'])

    op.execute("UPDATE remote_actions SET command_payload_json = '{}'::jsonb WHERE command_payload_json IS NULL")
    op.execute("UPDATE remote_actions SET command_signature = '' WHERE command_signature IS NULL")
    op.execute("UPDATE remote_actions SET signature_algorithm = 'HMAC_SHA256_PLACEHOLDER' WHERE signature_algorithm IS NULL")
    op.execute("UPDATE remote_actions SET acknowledgement_metadata_json = '{}'::jsonb WHERE acknowledgement_metadata_json IS NULL")

    op.alter_column('remote_actions', 'command_payload_json', nullable=False, server_default=None)
    op.alter_column('remote_actions', 'command_signature', nullable=False, server_default=None)
    op.alter_column('remote_actions', 'signature_algorithm', nullable=False, server_default=None)
    op.alter_column('remote_actions', 'acknowledgement_metadata_json', nullable=False, server_default=None)
    op.alter_column('remote_actions', 'attempt_count', server_default=None)

    op.create_table(
        'device_push_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('key_id', sa.String(length=80), nullable=False),
        sa.Column('push_token', sa.String(length=255), nullable=False),
        sa.Column('platform', sa.String(length=24), nullable=False),
        sa.Column('app_version', sa.String(length=40), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('invalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('push_token', name='uq_device_push_tokens_token'),
    )
    op.create_index('ix_device_push_tokens_org_device_active', 'device_push_tokens', ['org_id', 'device_id', 'is_active'])

    op.add_column('notification_events', sa.Column('remote_action_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('remote_actions.id'), nullable=True))
    op.add_column('notification_events', sa.Column('recipient_token', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('notification_events', 'recipient_token')
    op.drop_column('notification_events', 'remote_action_id')
    op.drop_index('ix_device_push_tokens_org_device_active', table_name='device_push_tokens')
    op.drop_table('device_push_tokens')
    op.drop_index('ix_remote_actions_device_state', table_name='remote_actions')
    for column in (
        'acknowledgement_metadata_json',
        'last_error',
        'attempt_count',
        'failed_at',
        'acked_at',
        'delivered_at',
        'sent_at',
        'expires_at',
        'signature_algorithm',
        'command_signature',
        'command_payload_json',
    ):
        op.drop_column('remote_actions', column)
