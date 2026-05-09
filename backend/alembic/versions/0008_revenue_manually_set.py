"""Add revenue_manually_set flag to companies

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS revenue_manually_set BOOLEAN NOT NULL DEFAULT false"
    ))


def downgrade():
    op.drop_column("companies", "revenue_manually_set")
