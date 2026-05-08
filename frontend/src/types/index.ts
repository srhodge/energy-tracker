export type EnergySegment =
  | "Integrated Gas" | "Onshore" | "Offshore" | "Combustion Energy"
  | "Midstream Infrastructure" | "Petrochemicals" | "Chemicals"
  | "Refined Fuels" | "Specialty Chemicals" | "Fuel Transport"
  | "Bulk Minerals" | "Agriculture Plants" | "Resource Infrastructure"
  | "Metals" | "Low Carbon Hydrogen" | "Renewable Energy" | "Energy Storage"
  | "Nuclear SMR" | "Power to X" | "Low Carbon Fuels" | "Direct Air Capture"
  | "Ammonia/Methanol" | "Plastics Recovery" | "Energy Transition Materials"
  | "Battery Materials" | "Water Recycling";

export type ValueChainPosition = "Upstream" | "Midstream" | "Downstream" | "Integrated" | "Services";
export type EnergyMaturity = "Mature" | "Developing";
export type EnergyCategory = "Energy" | "Chemicals" | "Resources";
export type EventType = "news" | "project" | "earnings" | "filing";

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
  energy_segment?: EnergySegment;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  latest_market_cap?: number;
  latest_price?: number;
  latest_revenue?: number;
}

export interface Financial {
  id: number;
  company_id: number;
  market_cap_usd?: number;
  price_usd?: number;
  revenue_annual_usd?: number;
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

export interface PaginatedCompanies {
  total: number;
  page: number;
  page_size: number;
  items: Company[];
}

export interface FilterOptions {
  wwt_territories: string[];
  countries: string[];
  energy_segments: EnergySegment[];
  value_chain_positions: ValueChainPosition[];
  supply_chain_positions: string[];
}
