"""Add ai_maturity_score to companies

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE companies ADD COLUMN IF NOT EXISTS ai_maturity_score INTEGER DEFAULT NULL"
    ))


def downgrade():
    op.drop_column("companies", "ai_maturity_score")
