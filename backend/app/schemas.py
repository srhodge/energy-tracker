from datetime import datetime, date
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models import EnergyMaturity, EnergyCategory, ValueChainPosition, EventType, CompanyStatus


class FinancialBase(BaseModel):
    market_cap_usd: Optional[float] = None
    price_usd: Optional[float] = None
    revenue_annual_usd: Optional[float] = None
    revenue_quarterly_usd: Optional[float] = None
    revenue_quarter_label: Optional[str] = None
    revenue_fiscal_year_label: Optional[str] = None
    snapshot_date: date


class FinancialOut(FinancialBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int


class EventBase(BaseModel):
    event_type: EventType
    title: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    event_date: Optional[date] = None


class EventOut(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    created_at: datetime


class EventWithCompany(EventOut):
    company_name: str
    company_ticker: Optional[str] = None


class CompanyBase(BaseModel):
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    wwt_territory: Optional[str] = None
    wwt_model: Optional[str] = None
    energy_maturity: Optional[EnergyMaturity] = None
    energy_category: Optional[EnergyCategory] = None
    industry: Optional[str] = None
    value_chain_position: Optional[ValueChainPosition] = None
    supply_chain_position: Optional[str] = None
    status: Optional[CompanyStatus] = CompanyStatus.active
    acquired_by: Optional[str] = None
    acquisition_notes: Optional[str] = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revenue_manually_set: bool = False
    latest_market_cap: Optional[float] = None
    latest_price: Optional[float] = None
    latest_revenue: Optional[float] = None
    latest_quarterly_revenue: Optional[float] = None
    latest_quarter_label: Optional[str] = None
    latest_fiscal_year_label: Optional[str] = None


class CompanyDetail(CompanyOut):
    financials: list[FinancialOut] = []
    events: list[EventOut] = []


class NewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    company_ticker: Optional[str] = None
    headline: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: datetime


class TerritoryRollup(BaseModel):
    wwt_territory: str
    company_count: int
    total_market_cap_usd: Optional[float] = None


class StatusSummary(BaseModel):
    Active: int = 0
    Acquired: int = 0
    Merged: int = 0
    Delisted: int = 0
    Unknown: int = 0


class PaginatedCompanies(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CompanyOut]


class CompanyLookupResult(BaseModel):
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    market_cap_usd: Optional[float] = None
    price_usd: Optional[float] = None
    currency: Optional[str] = None
    industry: Optional[str] = None
    value_chain_position: Optional[ValueChainPosition] = None
    supply_chain_position: Optional[str] = None
    wwt_territory: Optional[str] = None
    name_confidence: str = "high"
    country_confidence: str = "high"
    supply_chain_confidence: str = "low"
    wwt_territory_confidence: str = "low"
    already_exists: bool = False
    existing_id: Optional[int] = None
    error: Optional[str] = None


class CompanyAddRequest(BaseModel):
    ticker: Optional[str] = None
    name: str
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    wwt_territory: Optional[str] = None
    wwt_model: Optional[str] = None
    energy_maturity: Optional[EnergyMaturity] = None
    industry: Optional[str] = None
    value_chain_position: Optional[ValueChainPosition] = None
    supply_chain_position: Optional[str] = None
    is_public: bool = True


class CompanyAddResponse(BaseModel):
    id: int
    name: str
    ticker: Optional[str] = None


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = None
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    wwt_territory: Optional[str] = None
    wwt_model: Optional[str] = None
    energy_maturity: Optional[EnergyMaturity] = None
    industry: Optional[str] = None
    value_chain_position: Optional[ValueChainPosition] = None
    supply_chain_position: Optional[str] = None
    status: Optional[CompanyStatus] = None
    acquired_by: Optional[str] = None
    acquisition_notes: Optional[str] = None
    skip_market_poll: Optional[bool] = None
    revenue_manually_set: Optional[bool] = None
