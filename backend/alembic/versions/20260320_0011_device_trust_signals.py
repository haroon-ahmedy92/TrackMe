"""add advisory device trust signal storage

Revision ID: 20260320_0011
Revises: 20260319_0010
Create Date: 2026-03-20 09:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20260320_0011'
down_revision = '20260319_0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('last_seen_trust_status', sa.String(length=24), nullable=True))
    op.add_column('devices', sa.Column('last_seen_trust_summary', sa.String(length=280), nullable=True))
    op.add_column(
        'devices',
        sa.Column(
            'last_seen_trust_reasons_json',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column('devices', sa.Column('last_seen_integrity_status', sa.String(length=64), nullable=True))
    op.add_column('devices', sa.Column('last_seen_root_suspicion', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('devices', sa.Column('last_seen_debug_suspicion', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('devices', sa.Column('last_seen_mock_location_suspicion', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('devices', sa.Column('last_seen_trust_at', sa.DateTime(timezone=True), nullable=True))

    op.add_column('location_events', sa.Column('trust_status', sa.String(length=24), nullable=True))
    op.add_column('location_events', sa.Column('trust_summary', sa.String(length=280), nullable=True))
    op.add_column(
        'location_events',
        sa.Column(
            'trust_signals_json',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('location_events', 'trust_signals_json')
    op.drop_column('location_events', 'trust_summary')
    op.drop_column('location_events', 'trust_status')

    op.drop_column('devices', 'last_seen_trust_at')
    op.drop_column('devices', 'last_seen_mock_location_suspicion')
    op.drop_column('devices', 'last_seen_debug_suspicion')
    op.drop_column('devices', 'last_seen_root_suspicion')
    op.drop_column('devices', 'last_seen_integrity_status')
    op.drop_column('devices', 'last_seen_trust_reasons_json')
    op.drop_column('devices', 'last_seen_trust_summary')
    op.drop_column('devices', 'last_seen_trust_status')
