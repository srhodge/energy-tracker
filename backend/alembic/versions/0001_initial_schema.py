"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_energy_maturity = sa.Enum("Mature", "Developing", name="energymaturity")
_energy_category = sa.Enum("Energy", "Chemicals", "Resources", name="energycategory")
_energy_segment = sa.Enum(
    "Integrated Gas", "Onshore", "Offshore", "Combustion Energy",
    "Midstream Infrastructure", "Petrochemicals", "Chemicals",
    "Refined Fuels", "Specialty Chemicals", "Fuel Transport",
    "Bulk Minerals", "Agriculture Plants", "Resource Infrastructure",
    "Metals", "Low Carbon Hydrogen", "Renewable Energy", "Energy Storage",
    "Nuclear SMR", "Power to X", "Low Carbon Fuels", "Direct Air Capture",
    "Ammonia/Methanol", "Plastics Recovery", "Energy Transition Materials",
    "Battery Materials", "Water Recycling",
    name="energysegment",
)
_value_chain_position = sa.Enum(
    "Upstream", "Midstream", "Downstream", "Integrated", "Services",
    name="valuechainposition",
)
_event_type = sa.Enum("news", "project", "earnings", "filing", name="eventtype")


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("exchange", sa.String(50), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("wwt_territory", sa.String(50), nullable=True),
        sa.Column("wwt_model", sa.String(100), nullable=True),
        sa.Column("energy_maturity", _energy_maturity, nullable=True),
        sa.Column("energy_category", _energy_category, nullable=True),
        sa.Column("energy_segment", _energy_segment, nullable=True),
        sa.Column("value_chain_position", _value_chain_position, nullable=True),
        sa.Column("supply_chain_position", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_companies_id", "companies", ["id"])
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_ticker", "companies", ["ticker"])
    op.create_index("ix_companies_country", "companies", ["country"])
    op.create_index("ix_companies_wwt_territory", "companies", ["wwt_territory"])
    op.create_index("ix_companies_supply_chain_position", "companies", ["supply_chain_position"])

    op.create_table(
        "financials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("market_cap_usd", sa.Float(), nullable=True),
        sa.Column("price_usd", sa.Float(), nullable=True),
        sa.Column("revenue_annual_usd", sa.Float(), nullable=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financials_id", "financials", ["id"])
    op.create_index("ix_financials_company_id", "financials", ["company_id"])
    op.create_index("ix_financials_snapshot_date", "financials", ["snapshot_date"])

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("event_type", _event_type, nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.String(5000), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_id", "events", ["id"])
    op.create_index("ix_events_company_id", "events", ["company_id"])

    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("headline", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index("ix_news_items_id", "news_items", ["id"])
    op.create_index("ix_news_items_company_id", "news_items", ["company_id"])
    op.create_index("ix_news_items_published_at", "news_items", ["published_at"])


def downgrade() -> None:
    op.drop_table("news_items")
    op.drop_table("events")
    op.drop_table("financials")
    op.drop_table("companies")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for name in ["eventtype", "valuechainposition", "energysegment", "energycategory", "energymaturity"]:
            conn.execute(sa.text(f"DROP TYPE IF EXISTS {name}"))
