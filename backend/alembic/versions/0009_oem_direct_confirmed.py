"""Add oem_direct_confirmed flag to companies

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS oem_direct_confirmed BOOLEAN NOT NULL DEFAULT false"
    ))


def downgrade():
    op.drop_column("companies", "oem_direct_confirmed")
