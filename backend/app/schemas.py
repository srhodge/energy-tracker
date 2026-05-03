from datetime import datetime, date
from pydantic import BaseModel, ConfigDict
from typing import Optional
from app.models import EnergyMaturity, EnergyCategory, EnergySegment, ValueChainPosition, EventType


class FinancialBase(BaseModel):
    market_cap_usd: Optional[float] = None
    price_usd: Optional[float] = None
    revenue_annual_usd: Optional[float] = None
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
    energy_segment: Optional[EnergySegment] = None
    value_chain_position: Optional[ValueChainPosition] = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    latest_market_cap: Optional[float] = None
    latest_price: Optional[float] = None


class CompanyDetail(CompanyOut):
    financials: list[FinancialOut] = []
    events: list[EventOut] = []


class TerritoryRollup(BaseModel):
    wwt_territory: str
    company_count: int
    total_market_cap_usd: Optional[float] = None


class PaginatedCompanies(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CompanyOut]
