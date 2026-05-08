import type {
  PaginatedCompanies,
  CompanyDetail,
  TerritoryRollup,
  EventWithCompany,
  FilterOptions,
  EnergySegment,
  ValueChainPosition,
  EventType,
} from "../types";

const BASE = "https://energy-tracker-production-39a1.up.railway.app";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export interface CompanyListParams {
  wwt_territory?: string;
  energy_segment?: EnergySegment;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  country?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export function fetchCompanies(params: CompanyListParams = {}): Promise<PaginatedCompanies> {
  const q = new URLSearchParams();
  if (params.wwt_territory) q.set("wwt_territory", params.wwt_territory);
  if (params.energy_segment) q.set("energy_segment", params.energy_segment);
  if (params.value_chain_position) q.set("value_chain_position", params.value_chain_position);
  if (params.supply_chain_position) q.set("supply_chain_position", params.supply_chain_position);
  if (params.country) q.set("country", params.country);
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  const qs = q.toString();
  return get(`/companies${qs ? `?${qs}` : ""}`);
}

export function fetchCompany(id: number): Promise<CompanyDetail> {
  return get(`/companies/${id}`);
}

export function fetchCompanyByTicker(ticker: string): Promise<CompanyDetail> {
  return get(`/companies/by-ticker/${encodeURIComponent(ticker)}`);
}

export function fetchFilterOptions(): Promise<FilterOptions> {
  return get("/companies/filter-options");
}

export function fetchTerritoryRollup(): Promise<TerritoryRollup[]> {
  return get("/companies/territory-rollup");
}

export function fetchEvents(params: { event_type?: EventType; company_id?: number; limit?: number } = {}): Promise<EventWithCompany[]> {
  const q = new URLSearchParams();
  if (params.event_type) q.set("event_type", params.event_type);
  if (params.company_id) q.set("company_id", String(params.company_id));
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return get(`/events${qs ? `?${qs}` : ""}`);
}
