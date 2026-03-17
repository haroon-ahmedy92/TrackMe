"""add event queue and rule execution locks

Revision ID: 20260317_0008
Revises: 20260315_0007
Create Date: 2026-03-17 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260317_0008'
down_revision = '20260315_0007'
branch_labels = None
depends_on = None


queuedeventstatus = sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='queuedeventstatus')


def upgrade() -> None:
    bind = op.get_bind()
    queuedeventstatus.create(bind, checkfirst=True)

    op.create_table(
        'event_queue_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=True),
        sa.Column('topic', sa.String(length=120), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.String(length=120), nullable=False),
        sa.Column('producer', sa.String(length=120), nullable=False),
        sa.Column('idempotency_key', sa.String(length=160), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('headers_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('status', queuedeventstatus, nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_by', sa.String(length=120), nullable=True),
        sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.String(length=280), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('idempotency_key', name='uq_event_queue_items_idempotency'),
    )
    op.create_index('ix_event_queue_items_status_available', 'event_queue_items', ['status', 'available_at'])
    op.create_index('ix_event_queue_items_topic_created', 'event_queue_items', ['topic', 'created_at'])

    op.create_table(
        'rule_execution_locks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=True),
        sa.Column('rule_code', sa.String(length=120), nullable=False),
        sa.Column('scope_key', sa.String(length=180), nullable=False),
        sa.Column('last_event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('event_queue_items.id'), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('org_id', 'rule_code', 'scope_key', name='uq_rule_execution_locks_scope'),
    )
    op.create_index('ix_rule_execution_locks_cooldown', 'rule_execution_locks', ['cooldown_until'])


def downgrade() -> None:
    op.drop_index('ix_rule_execution_locks_cooldown', table_name='rule_execution_locks')
    op.drop_table('rule_execution_locks')

    op.drop_index('ix_event_queue_items_topic_created', table_name='event_queue_items')
    op.drop_index('ix_event_queue_items_status_available', table_name='event_queue_items')
    op.drop_table('event_queue_items')

    bind = op.get_bind()
    queuedeventstatus.drop(bind, checkfirst=True)
