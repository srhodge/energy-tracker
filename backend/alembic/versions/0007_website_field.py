"""add website field to companies

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS website VARCHAR(500)"))


def downgrade() -> None:
    op.drop_column("companies", "website")
