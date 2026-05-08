"""add Sanctioned and Non-Equity status values

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        # ALTER TYPE ADD VALUE must run outside a transaction block
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'Sanctioned'"))
            op.execute(sa.text("ALTER TYPE companystatus ADD VALUE IF NOT EXISTS 'Non-Equity'"))
    # SQLite stores enums as VARCHAR — no DDL change needed


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values; downgrade is a no-op
    pass
