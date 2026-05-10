from datetime import datetime, date
from decimal import Decimal
from typing import Any
from sqlalchemy import (
    String, Integer, Float, Date, DateTime, Boolean, Text, Numeric,
    ForeignKey, Enum as SAEnum, JSON,
)
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
    sub_sector: Mapped[str | None] = mapped_column(String(100))

    skip_market_poll: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    revenue_manually_set: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[CompanyStatus] = mapped_column(
        _enum(CompanyStatus), nullable=False, default=CompanyStatus.active, server_default="Active"
    )
    acquired_by: Mapped[str | None] = mapped_column(String(200))
    acquisition_notes: Mapped[str | None] = mapped_column(String(500))

    # Headcount
    employee_count: Mapped[int | None] = mapped_column(Integer)
    employee_count_source: Mapped[str | None] = mapped_column(String(50))
    employee_count_updated: Mapped[date | None] = mapped_column(Date)

    # Geography
    hq_city: Mapped[str | None] = mapped_column(String(100))
    hq_country: Mapped[str | None] = mapped_column(String(100))
    tech_decision_city: Mapped[str | None] = mapped_column(String(100))
    tech_decision_country: Mapped[str | None] = mapped_column(String(100))

    # Financials (TTM/point-in-time, separate from the time-series financials table)
    revenue_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    ebitda_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    gross_profit_ttm: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    enterprise_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    revenue_denominator: Mapped[str | None] = mapped_column(String(20), server_default="revenue")

    # Classification flags
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_pe_backed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    commodity_exposure_pct: Mapped[int | None] = mapped_column(Integer)

    # Enrichment / model metadata
    ms_standardized: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    offshore_coe_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    incumbent_msp: Mapped[str | None] = mapped_column(String(200))
    channel_mismatch_flag: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    channel_mismatch_note: Mapped[str | None] = mapped_column(Text)
    data_enrichment_tier: Mapped[int | None] = mapped_column(Integer)

    financials: Mapped[list["Financial"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    news_items: Mapped[list["NewsItem"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    tech_signals: Mapped[list["CompanyTechSignal"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    spend_estimates: Mapped[list["CompanySpendEstimate"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    leadership: Mapped[list["CompanyLeadership"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    assets: Mapped[list["CompanyAsset"]] = relationship(back_populates="company", cascade="all, delete-orphan")


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

    # Extended metrics for spend model
    ebitda_annual_usd: Mapped[float | None] = mapped_column(Float)
    gross_profit_annual_usd: Mapped[float | None] = mapped_column(Float)
    enterprise_value_usd: Mapped[float | None] = mapped_column(Float)
    ps_ratio: Mapped[float | None] = mapped_column(Float)
    ps_ratio_5yr_avg: Mapped[float | None] = mapped_column(Float)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)

    energy_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float)
    match_method: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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


class CompanyTechSignal(Base):
    __tablename__ = "company_tech_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_category: Mapped[str | None] = mapped_column(String(20))
    signal_date: Mapped[date | None] = mapped_column(Date, index=True)
    signal_title: Mapped[str | None] = mapped_column(Text)
    signal_description: Mapped[str | None] = mapped_column(Text)
    signal_url: Mapped[str | None] = mapped_column(Text)
    sentiment: Mapped[str | None] = mapped_column(String(10))
    spend_impact_direction: Mapped[str | None] = mapped_column(String(10))
    score_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source: Mapped[str | None] = mapped_column(String(50))
    week_batch_date: Mapped[date | None] = mapped_column(Date, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="tech_signals")


class CompanySpendEstimate(Base):
    __tablename__ = "company_spend_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    estimate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    estimate_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    fiscal_year: Mapped[int | None] = mapped_column(Integer)

    it_spend_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    it_spend_mid: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    it_spend_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ot_spend_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ot_spend_mid: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ot_spend_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    digital_spend_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    digital_spend_mid: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    digital_spend_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ai_spend_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ai_spend_mid: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    ai_spend_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_spend_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_spend_mid: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_spend_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    wwt_addressable_low: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    wwt_addressable_high: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    wwt_addressable_pct_low: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    wwt_addressable_pct_high: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    confidence_level: Mapped[str | None] = mapped_column(String(10))
    model_version: Mapped[str | None] = mapped_column(String(10), server_default="v3.0")

    # Model step audit trail
    step1_value_chain: Mapped[str | None] = mapped_column(String(100))
    step2_denominator_used: Mapped[str | None] = mapped_column(String(20))
    step3_regional_multiplier: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    step6_it_maturity_score: Mapped[int | None] = mapped_column(Integer)
    step6_ot_maturity_score: Mapped[int | None] = mapped_column(Integer)
    step6_digital_maturity_score: Mapped[int | None] = mapped_column(Integer)
    step6_ai_maturity_score: Mapped[int | None] = mapped_column(Integer)
    step9_commodity_adjustment: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    step10_addressable_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    key_drivers: Mapped[Any | None] = mapped_column(JSON)
    flags: Mapped[Any | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="spend_estimates")


class CompanyLeadership(Base):
    __tablename__ = "company_leadership"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    person_name: Mapped[str | None] = mapped_column(String(200))
    location_city: Mapped[str | None] = mapped_column(String(100))
    location_country: Mapped[str | None] = mapped_column(String(100))
    hire_date: Mapped[date | None] = mapped_column(Date)
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    departure_date: Mapped[date | None] = mapped_column(Date)
    spend_category: Mapped[str | None] = mapped_column(String(20))
    signal_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="leadership")


class CompanyAsset(Base):
    __tablename__ = "company_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    asset_category: Mapped[str | None] = mapped_column(String(20), index=True)
    asset_value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    asset_unit: Mapped[str | None] = mapped_column(String(50))
    asset_score: Mapped[int | None] = mapped_column(Integer)
    data_source: Mapped[str | None] = mapped_column(String(100))
    as_of_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company: Mapped["Company | None"] = relationship(back_populates="assets")
