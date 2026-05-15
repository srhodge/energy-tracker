"""Add client executive fields to companies

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS ce_name VARCHAR(200) DEFAULT NULL"
    ))
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS ce_email VARCHAR(200) DEFAULT NULL"
    ))
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS ce_phone VARCHAR(50) DEFAULT NULL"
    ))


def downgrade():
    op.drop_column("companies", "ce_phone")
    op.drop_column("companies", "ce_email")
    op.drop_column("companies", "ce_name")
