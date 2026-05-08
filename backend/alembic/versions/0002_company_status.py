"""company status fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_status_enum = sa.Enum(
    "Active", "Acquired", "Merged", "Delisted", "Unknown",
    name="companystatus",
)


def upgrade() -> None:
    # create_type=True is the default; for SQLite it's a no-op
    _status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column("companies", sa.Column(
        "status", _status_enum, nullable=False, server_default="Active"
    ))
    op.add_column("companies", sa.Column("acquired_by", sa.String(200), nullable=True))
    op.add_column("companies", sa.Column("acquisition_notes", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "acquisition_notes")
    op.drop_column("companies", "acquired_by")
    op.drop_column("companies", "status")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP TYPE IF EXISTS companystatus"))
