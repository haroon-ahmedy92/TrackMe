"""add ownership binding, pairing, transfer, and access review tables

Revision ID: 20260313_0002
Revises: 20260310_0001
Create Date: 2026-03-13 09:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260313_0002'
down_revision = '20260310_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'security_operator'")

    ownership_type = postgresql.ENUM('single_user', 'organization_owned', name='ownershiptype')
    ownership_proof_kind = postgresql.ENUM(
        'enrollment_token',
        'qr_code',
        'admin_approval',
        'transfer_approval',
        'manual_review',
        name='ownershipproofkind',
    )
    access_review_status = postgresql.ENUM('pending', 'approved', 'rejected', name='accessreviewstatus')
    ownership_transfer_status = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', name='ownershiptransferstatus')

    for enum_type in (
        ownership_type,
        ownership_proof_kind,
        access_review_status,
        ownership_transfer_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        'device_ownership_bindings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('ownership_type', ownership_type, nullable=False),
        sa.Column('proof_kind', ownership_proof_kind, nullable=False),
        sa.Column('proof_reference', sa.String(length=180), nullable=True),
        sa.Column('consent_version', sa.String(length=40), nullable=False),
        sa.Column('consent_captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bound_by_sub', sa.String(length=150), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        'ix_device_ownership_bindings_org_device_active',
        'device_ownership_bindings',
        ['org_id', 'device_id', 'is_active'],
    )

    op.create_table(
        'device_access_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('owner_can_locate', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('admin_can_locate', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('security_operator_can_review', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('require_access_review', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('device_id', name='uq_device_access_policies_device'),
    )

    op.create_table(
        'pairing_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('enrollment_type', postgresql.ENUM(name='enrollmenttype', create_type=False), nullable=False),
        sa.Column('ownership_type', ownership_type, nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('token_hint', sa.String(length=16), nullable=False),
        sa.Column('issued_by_sub', sa.String(length=150), nullable=False),
        sa.Column('proof_kind', ownership_proof_kind, nullable=False),
        sa.Column('consent_version', sa.String(length=40), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('token_hash', name='uq_pairing_tokens_hash'),
    )
    op.create_index('ix_pairing_tokens_org_expires', 'pairing_tokens', ['org_id', 'expires_at'])

    op.create_table(
        'ownership_transfers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('from_owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('to_owner_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('approved_by_sub', sa.String(length=150), nullable=True),
        sa.Column('status', ownership_transfer_status, nullable=False),
        sa.Column('reason', sa.String(length=280), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_ownership_transfers_org_device_created', 'ownership_transfers', ['org_id', 'device_id', 'created_at'])

    op.create_table(
        'access_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('reviewed_by_sub', sa.String(length=150), nullable=True),
        sa.Column('status', access_review_status, nullable=False),
        sa.Column('rationale', sa.String(length=280), nullable=False),
        sa.Column('review_notes', sa.String(length=280), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_access_reviews_org_device_created', 'access_reviews', ['org_id', 'device_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_access_reviews_org_device_created', table_name='access_reviews')
    op.drop_table('access_reviews')
    op.drop_index('ix_ownership_transfers_org_device_created', table_name='ownership_transfers')
    op.drop_table('ownership_transfers')
    op.drop_index('ix_pairing_tokens_org_expires', table_name='pairing_tokens')
    op.drop_table('pairing_tokens')
    op.drop_table('device_access_policies')
    op.drop_index('ix_device_ownership_bindings_org_device_active', table_name='device_ownership_bindings')
    op.drop_table('device_ownership_bindings')

    bind = op.get_bind()
    for enum_name in ('ownershiptransferstatus', 'accessreviewstatus', 'ownershipproofkind', 'ownershiptype'):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
