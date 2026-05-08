export type ValueChainPosition = "Upstream" | "Midstream" | "Downstream" | "Integrated" | "Services";
export type EnergyMaturity = "Mature" | "Developing";
export type EnergyCategory = "Energy" | "Chemicals" | "Resources";
export type EventType = "news" | "project" | "earnings" | "filing";
export type CompanyStatus = "Active" | "Acquired" | "Merged" | "Delisted" | "Unknown" | "Sanctioned" | "Non-Equity";

export interface Company {
  id: number;
  name: string;
  ticker?: string;
  exchange?: string;
  country?: string;
  website?: string;
  description?: string;
  wwt_territory?: string;
  wwt_model?: string;
  energy_maturity?: EnergyMaturity;
  energy_category?: EnergyCategory;
  industry?: string;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  status?: CompanyStatus;
  acquired_by?: string;
  acquisition_notes?: string;
  latest_market_cap?: number;
  latest_price?: number;
  latest_revenue?: number;
  latest_quarterly_revenue?: number;
  latest_quarter_label?: string;
  latest_fiscal_year_label?: string;
}

export interface StatusSummary {
  Active: number;
  Acquired: number;
  Merged: number;
  Delisted: number;
  Unknown: number;
  Sanctioned: number;
  "Non-Equity": number;
}

export interface Financial {
  id: number;
  company_id: number;
  market_cap_usd?: number;
  price_usd?: number;
  revenue_annual_usd?: number;
  revenue_quarterly_usd?: number;
  revenue_quarter_label?: string;
  revenue_fiscal_year_label?: string;
  snapshot_date: string;
}

export interface Event {
  id: number;
  company_id: number;
  event_type: EventType;
  title: string;
  summary?: string;
  source_url?: string;
  event_date?: string;
  created_at: string;
}

export interface EventWithCompany extends Event {
  company_name: string;
  company_ticker?: string;
}

export interface CompanyDetail extends Company {
  financials: Financial[];
  events: Event[];
}

export interface TerritoryRollup {
  wwt_territory: string;
  company_count: number;
  total_market_cap_usd?: number;
}

export interface SupplyChainRollup {
  supply_chain_position: string;
  company_count: number;
  total_market_cap_usd?: number;
}

export interface NewsItem {
  id: number;
  company_id?: number;
  company_name?: string;
  company_ticker?: string;
  headline: string;
  source?: string;
  source_url?: string;
  published_at?: string;
  fetched_at: string;
}

export interface PaginatedCompanies {
  total: number;
  page: number;
  page_size: number;
  items: Company[];
}

export interface FilterOptions {
  wwt_territories: string[];
  countries: string[];
  industries: string[];
  value_chain_positions: ValueChainPosition[];
  supply_chain_positions: string[];
}

export interface CompanyLookupResult {
  name: string;
  ticker?: string;
  exchange?: string;
  country?: string;
  website?: string;
  description?: string;
  market_cap_usd?: number;
  price_usd?: number;
  currency?: string;
  industry?: string;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  wwt_territory?: string;
  name_confidence: string;
  country_confidence: string;
  supply_chain_confidence: string;
  wwt_territory_confidence: string;
  already_exists: boolean;
  existing_id?: number;
  error?: string;
}

export interface CompanyAddRequest {
  ticker?: string;
  name: string;
  exchange?: string;
  country?: string;
  website?: string;
  description?: string;
  wwt_territory?: string;
  wwt_model?: string;
  energy_maturity?: EnergyMaturity;
  industry?: string;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  is_public: boolean;
}

export interface CompanyAddResponse {
  id: number;
  name: string;
  ticker?: string;
}

export interface CompanyUpdateRequest {
  name?: string;
  ticker?: string;
  exchange?: string;
  country?: string;
  website?: string;
  description?: string;
  wwt_territory?: string;
  wwt_model?: string;
  energy_maturity?: EnergyMaturity;
  industry?: string;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  status?: CompanyStatus;
  acquired_by?: string;
  acquisition_notes?: string;
}
