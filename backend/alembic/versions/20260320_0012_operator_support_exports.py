"""add operator assignment and csv evidence export support

Revision ID: 20260320_0012
Revises: 20260320_0011
Create Date: 2026-03-20 16:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = '20260320_0012'
down_revision = '20260320_0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE evidenceexportformat ADD VALUE IF NOT EXISTS 'csv'")
    op.add_column('incidents', sa.Column('assigned_operator_sub', sa.String(length=150), nullable=True))
    op.create_index(
        'ix_incidents_org_assigned_updated',
        'incidents',
        ['org_id', 'assigned_operator_sub', 'updated_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_incidents_org_assigned_updated', table_name='incidents')
    op.drop_column('incidents', 'assigned_operator_sub')
