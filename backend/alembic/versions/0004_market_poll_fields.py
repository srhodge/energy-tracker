"""add skip_market_poll and last_market_update

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column(
        "skip_market_poll", sa.Boolean(), nullable=False, server_default="false"
    ))
    op.add_column("financials", sa.Column(
        "last_market_update", sa.DateTime(), nullable=True
    ))


def downgrade() -> None:
    op.drop_column("financials", "last_market_update")
    op.drop_column("companies", "skip_market_poll")
