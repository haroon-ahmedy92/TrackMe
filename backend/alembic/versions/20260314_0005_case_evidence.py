"""add case evidence notes attachments and exports

Revision ID: 20260314_0005
Revises: 20260314_0004
Create Date: 2026-03-14 21:45:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260314_0005'
down_revision = '20260314_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    evidence_export_format = postgresql.ENUM('json', 'pdf', name='evidenceexportformat')
    evidence_export_status = postgresql.ENUM('generated', 'failed', name='evidenceexportstatus')
    evidence_export_format.create(op.get_bind(), checkfirst=True)
    evidence_export_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'incident_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('author_sub', sa.String(length=150), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incident_notes_incident_updated', 'incident_notes', ['incident_id', 'updated_at'])

    op.create_table(
        'incident_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('uploaded_by_sub', sa.String(length=150), nullable=False),
        sa.Column('file_name', sa.String(length=180), nullable=False),
        sa.Column('media_type', sa.String(length=120), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=128), nullable=True),
        sa.Column('description', sa.String(length=280), nullable=True),
        sa.Column('storage_key', sa.String(length=220), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_incident_attachments_incident_created', 'incident_attachments', ['incident_id', 'created_at'])

    op.create_table(
        'evidence_exports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orgs.id'), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('requested_by_sub', sa.String(length=150), nullable=False),
        sa.Column('format', evidence_export_format, nullable=False),
        sa.Column('status', evidence_export_status, nullable=False),
        sa.Column('reason', sa.String(length=280), nullable=False),
        sa.Column('redact_fields_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_evidence_exports_incident_created', 'evidence_exports', ['incident_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_evidence_exports_incident_created', table_name='evidence_exports')
    op.drop_table('evidence_exports')
    op.drop_index('ix_incident_attachments_incident_created', table_name='incident_attachments')
    op.drop_table('incident_attachments')
    op.drop_index('ix_incident_notes_incident_updated', table_name='incident_notes')
    op.drop_table('incident_notes')
    postgresql.ENUM(name='evidenceexportstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='evidenceexportformat').drop(op.get_bind(), checkfirst=True)
