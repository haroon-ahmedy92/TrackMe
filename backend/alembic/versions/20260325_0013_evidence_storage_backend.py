"""add storage backend metadata for incident attachments

Revision ID: 20260325_0013
Revises: 20260320_0012
Create Date: 2026-03-25 09:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260325_0013'
down_revision = '20260320_0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('incident_attachments', sa.Column('storage_backend', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('incident_attachments', 'storage_backend')
