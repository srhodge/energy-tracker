"""add industry field to companies, seeded from energy_segment

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("industry", sa.String(150), nullable=True))
    # Seed from energy_segment as fallback; yfinance will overwrite on next fundamentals poll
    op.execute("UPDATE companies SET industry = energy_segment WHERE energy_segment IS NOT NULL")


def downgrade() -> None:
    op.drop_column("companies", "industry")
