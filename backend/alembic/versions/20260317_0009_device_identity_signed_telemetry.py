"""device identity hardening and signed telemetry metadata

Revision ID: 20260317_0009
Revises: 20260317_0008
Create Date: 2026-03-17 18:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '20260317_0009'
down_revision = '20260317_0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('device_keys', sa.Column('is_hardware_backed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('device_keys', sa.Column('attestation_format', sa.String(length=48), nullable=True))
    op.add_column('device_keys', sa.Column('attestation_record', sa.Text(), nullable=True))
    op.add_column('device_keys', sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('device_keys', sa.Column('revoked_reason', sa.String(length=280), nullable=True))
    op.add_column('device_keys', sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('device_keys', 'is_hardware_backed', server_default=None)

    op.add_column('location_events', sa.Column('telemetry_algorithm', sa.String(length=40), nullable=True))
    op.add_column('location_events', sa.Column('telemetry_payload_hash', sa.String(length=128), nullable=True))
    op.add_column('location_events', sa.Column('telemetry_verification_reason', sa.String(length=80), nullable=True))

    op.add_column('telemetry_events', sa.Column('telemetry_payload_hash', sa.String(length=128), nullable=True))
    op.add_column('telemetry_events', sa.Column('telemetry_verification_reason', sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column('telemetry_events', 'telemetry_verification_reason')
    op.drop_column('telemetry_events', 'telemetry_payload_hash')

    op.drop_column('location_events', 'telemetry_verification_reason')
    op.drop_column('location_events', 'telemetry_payload_hash')
    op.drop_column('location_events', 'telemetry_algorithm')

    op.drop_column('device_keys', 'last_used_at')
    op.drop_column('device_keys', 'revoked_reason')
    op.drop_column('device_keys', 'revoked_at')
    op.drop_column('device_keys', 'attestation_record')
    op.drop_column('device_keys', 'attestation_format')
    op.drop_column('device_keys', 'is_hardware_backed')
