from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


def _enum(py_enum):
    """SAEnum that stores .value ('Mature') not .name ('mature')."""
    return SAEnum(py_enum, values_callable=lambda members: [m.value for m in members])


class EnergyMaturity(str, enum.Enum):
    mature = "Mature"
    developing = "Developing"


class EnergyCategory(str, enum.Enum):
    energy = "Energy"
    chemicals = "Chemicals"
    resources = "Resources"


class EnergySegment(str, enum.Enum):
    integrated_gas = "Integrated Gas"
    onshore = "Onshore"
    offshore = "Offshore"
    combustion_energy = "Combustion Energy"
    midstream_infrastructure = "Midstream Infrastructure"
    petrochemicals = "Petrochemicals"
    chemicals = "Chemicals"
    refined_fuels = "Refined Fuels"
    specialty_chemicals = "Specialty Chemicals"
    fuel_transport = "Fuel Transport"
    bulk_minerals = "Bulk Minerals"
    agriculture_plants = "Agriculture Plants"
    resource_infrastructure = "Resource Infrastructure"
    metals = "Metals"
    low_carbon_hydrogen = "Low Carbon Hydrogen"
    renewable_energy = "Renewable Energy"
    energy_storage = "Energy Storage"
    nuclear_smr = "Nuclear SMR"
    power_to_x = "Power to X"
    low_carbon_fuels = "Low Carbon Fuels"
    direct_air_capture = "Direct Air Capture"
    ammonia_methanol = "Ammonia/Methanol"
    plastics_recovery = "Plastics Recovery"
    energy_transition_materials = "Energy Transition Materials"
    battery_materials = "Battery Materials"
    water_recycling = "Water Recycling"


class ValueChainPosition(str, enum.Enum):
    upstream = "Upstream"
    midstream = "Midstream"
    downstream = "Downstream"
    integrated = "Integrated"
    services = "Services"


class EventType(str, enum.Enum):
    news = "news"
    project = "project"
    earnings = "earnings"
    filing = "filing"


class CompanyStatus(str, enum.Enum):
    active = "Active"
    acquired = "Acquired"
    merged = "Merged"
    delisted = "Delisted"
    unknown = "Unknown"
    sanctioned = "Sanctioned"
    non_equity = "Non-Equity"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(20), index=True)
    exchange: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100), index=True)
    website: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(2000))

    wwt_territory: Mapped[str | None] = mapped_column(String(50), index=True)
    wwt_model: Mapped[str | None] = mapped_column(String(100))

    energy_maturity: Mapped[EnergyMaturity | None] = mapped_column(_enum(EnergyMaturity))
    energy_category: Mapped[EnergyCategory | None] = mapped_column(_enum(EnergyCategory))
    energy_segment: Mapped[EnergySegment | None] = mapped_column(_enum(EnergySegment))
    industry: Mapped[str | None] = mapped_column(String(150))
    value_chain_position: Mapped[ValueChainPosition | None] = mapped_column(_enum(ValueChainPosition))
    supply_chain_position: Mapped[str | None] = mapped_column(String(50), index=True)
    skip_market_poll: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    revenue_manually_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[CompanyStatus] = mapped_column(
        _enum(CompanyStatus), nullable=False, default=CompanyStatus.active, server_default="Active"
    )
    acquired_by: Mapped[str | None] = mapped_column(String(200))
    acquisition_notes: Mapped[str | None] = mapped_column(String(500))

    financials: Mapped[list["Financial"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    news_items: Mapped[list["NewsItem"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Financial(Base):
    __tablename__ = "financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    market_cap_usd: Mapped[float | None] = mapped_column(Float)
    price_usd: Mapped[float | None] = mapped_column(Float)
    revenue_annual_usd: Mapped[float | None] = mapped_column(Float)
    revenue_quarterly_usd: Mapped[float | None] = mapped_column(Float)
    revenue_quarter_label: Mapped[str | None] = mapped_column(String(10))
    revenue_fiscal_year_label: Mapped[str | None] = mapped_column(String(10))
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    last_market_update: Mapped[datetime | None] = mapped_column(DateTime)

    company: Mapped["Company"] = relationship(back_populates="financials")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(_enum(EventType), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(5000))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    event_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="events")


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    headline: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(1000), unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company | None"] = relationship(back_populates="news_items")


class CrmAccount(Base):
    __tablename__ = "crm_accounts"

    id:   Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    opportunities: Mapped[list["CrmOpportunity"]] = relationship(back_populates="account")


class CrmOpportunity(Base):
    __tablename__ = "crm_opportunities"

    id:                 Mapped[int]         = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id:         Mapped[int | None]  = mapped_column(ForeignKey("crm_accounts.id"), nullable=True, index=True)
    account_name:       Mapped[str | None]  = mapped_column(String(500))
    owner_role:         Mapped[str | None]  = mapped_column(String(200))
    opportunity_owner:  Mapped[str | None]  = mapped_column(String(200))
    opportunity_name:   Mapped[str | None]  = mapped_column(String(2000))
    stage:              Mapped[str | None]  = mapped_column(String(200), index=True)
    fiscal_period:      Mapped[str | None]  = mapped_column(String(50))
    amount:             Mapped[float | None] = mapped_column(Float)
    probability:        Mapped[float | None] = mapped_column(Float)
    age:                Mapped[float | None] = mapped_column(Float)
    close_date:         Mapped[date | None]  = mapped_column(Date)
    created_date:       Mapped[date | None]  = mapped_column(Date)
    next_step:          Mapped[str | None]  = mapped_column(String(2000))
    lead_source:        Mapped[str | None]  = mapped_column(String(200))
    opp_type:           Mapped[str | None]  = mapped_column(String(200))

    account: Mapped["CrmAccount | None"] = relationship(back_populates="opportunities")
