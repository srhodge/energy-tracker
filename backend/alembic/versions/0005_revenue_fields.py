"""add quarterly revenue and period labels to financials

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("financials", sa.Column("revenue_quarterly_usd", sa.Float(), nullable=True))
    op.add_column("financials", sa.Column("revenue_quarter_label", sa.String(10), nullable=True))
    op.add_column("financials", sa.Column("revenue_fiscal_year_label", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("financials", "revenue_fiscal_year_label")
    op.drop_column("financials", "revenue_quarter_label")
    op.drop_column("financials", "revenue_quarterly_usd")
