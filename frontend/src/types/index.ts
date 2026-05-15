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
  revenue_manually_set?: boolean;
  latest_market_cap?: number;
  latest_price?: number;
  latest_revenue?: number;
  latest_quarterly_revenue?: number;
  latest_quarter_label?: string;
  latest_fiscal_year_label?: string;
  ce_name?: string;
  ce_email?: string;
  ce_phone?: string;
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
  total_revenue_usd?: number;
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

export interface ScatterPoint {
  id: number;
  name: string;
  ticker?: string;
  supply_chain_position?: string;
  country?: string;
  territory?: string;
  revenue_annual_usd: number;
  revenue_fiscal_year_label?: string;
  market_cap_usd: number;
}

export interface ScatterData {
  total_companies: number;
  included_count: number;
  items: ScatterPoint[];
}

export interface SegmentChartRow {
  segment: string;
  company_count: number;
  median_ps: number;
  revenue_share: number;
  cap_share: number;
  total_revenue: number;
  total_cap: number;
  implied_ps: number;
}

export interface TerritoryChartRow {
  territory: string;
  company_count: number;
  median_cap: number;
  total_cap: number;
}

export interface ChartsData {
  by_segment: SegmentChartRow[];
  by_territory: TerritoryChartRow[];
  overall_median_ps: number;
  filters_applied: {
    territory: string;
    country: string;
    value_chain: string;
    ps_filter: string;
  };
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
  revenue_manually_set?: boolean;
  ce_name?: string;
  ce_email?: string;
  ce_phone?: string;
}

// ── Intelligence ──────────────────────────────────────────────────────────────

export interface IntelligenceProfile {
  sub_sector?: string;
  employee_count?: number;
  employee_count_source?: string;
  employee_count_updated?: string;
  hq_city?: string;
  hq_country?: string;
  tech_decision_city?: string;
  tech_decision_country?: string;
  revenue_ttm?: number;
  ebitda_ttm?: number;
  gross_profit_ttm?: number;
  enterprise_value?: number;
  revenue_denominator?: string;
  is_private?: boolean;
  is_pe_backed?: boolean;
  commodity_exposure_pct?: number;
  ms_standardized?: boolean;
  offshore_coe_confirmed?: boolean;
  incumbent_msp?: string;
  channel_mismatch_flag?: boolean;
  channel_mismatch_note?: string;
  oem_direct_confirmed?: boolean;
  data_enrichment_tier?: number;
  ai_maturity_score?: number;
  ce_name?: string;
  ce_email?: string;
  ce_phone?: string;
}

export interface TechSignal {
  id: number;
  company_id?: number;
  signal_type: string;
  signal_category?: string;
  signal_date?: string;
  signal_title?: string;
  signal_description?: string;
  signal_url?: string;
  sentiment?: string;
  spend_impact_direction?: string;
  score_points: number;
  source?: string;
  week_batch_date?: string;
  created_at?: string;
}

export interface LeadershipRecord {
  id: number;
  company_id?: number;
  role: string;
  person_name?: string;
  location_city?: string;
  location_country?: string;
  hire_date?: string;
  linkedin_url?: string;
  is_current: boolean;
  departure_date?: string;
  spend_category?: string;
  signal_score: number;
  source?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SpendEstimate {
  id: number;
  company_id?: number;
  estimate_date: string;
  estimate_type: string;
  fiscal_year?: number;
  it_spend_low?: number;
  it_spend_mid?: number;
  it_spend_high?: number;
  ot_spend_low?: number;
  ot_spend_mid?: number;
  ot_spend_high?: number;
  digital_spend_low?: number;
  digital_spend_mid?: number;
  digital_spend_high?: number;
  ai_spend_low?: number;
  ai_spend_mid?: number;
  ai_spend_high?: number;
  total_spend_low?: number;
  total_spend_mid?: number;
  total_spend_high?: number;
  wwt_addressable_low?: number;
  wwt_addressable_high?: number;
  wwt_addressable_pct_low?: number;
  wwt_addressable_pct_high?: number;
  confidence_level?: string;
  model_version?: string;
  step1_value_chain?: string;
  step2_denominator_used?: string;
  step3_regional_multiplier?: number;
  key_drivers?: Record<string, unknown>;
  flags?: Record<string, unknown>;
  notes?: string;
  created_at?: string;
}

export interface IntelligenceData {
  profile: IntelligenceProfile;
  signals: TechSignal[];
  leadership: LeadershipRecord[];
  latest_estimate: SpendEstimate | null;
}
