"""add misplaced check-in mode

Revision ID: 20260314_0006
Revises: 20260314_0005
Create Date: 2026-03-14 21:10:00
"""

from alembic import op


revision = '20260314_0006'
down_revision = '20260314_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE checkinmode ADD VALUE IF NOT EXISTS 'misplaced'")


def downgrade() -> None:
    # Postgres enum value removal is intentionally not automated.
    pass
