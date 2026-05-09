import type {
  PaginatedCompanies,
  CompanyDetail,
  Company,
  TerritoryRollup,
  SupplyChainRollup,
  NewsItem,
  EventWithCompany,
  FilterOptions,
  StatusSummary,
  ValueChainPosition,
  EventType,
  CompanyLookupResult,
  CompanyAddRequest,
  CompanyAddResponse,
  CompanyUpdateRequest,
} from "../types";

const BASE = "https://energy-tracker-production-39a1.up.railway.app";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export interface CompanyListParams {
  wwt_territory?: string;
  industry?: string;
  value_chain_position?: ValueChainPosition;
  supply_chain_position?: string;
  country?: string;
  search?: string;
  include_inactive?: boolean;
  status?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export function fetchCompanies(params: CompanyListParams = {}): Promise<PaginatedCompanies> {
  const q = new URLSearchParams();
  if (params.wwt_territory) q.set("wwt_territory", params.wwt_territory);
  if (params.industry) q.set("industry", params.industry);
  if (params.value_chain_position) q.set("value_chain_position", params.value_chain_position);
  if (params.supply_chain_position) q.set("supply_chain_position", params.supply_chain_position);
  if (params.country) q.set("country", params.country);
  if (params.search) q.set("search", params.search);
  if (params.include_inactive) q.set("include_inactive", "true");
  if (params.status) q.set("status", params.status);
  if (params.sort_by) q.set("sort_by", params.sort_by);
  if (params.sort_dir) q.set("sort_dir", params.sort_dir);
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

export function fetchSupplyChainRollup(): Promise<SupplyChainRollup[]> {
  return get("/companies/supply-chain-rollup");
}

export function fetchStatusSummary(): Promise<StatusSummary> {
  return get("/companies/status-summary");
}

export function fetchNews(limit = 50): Promise<NewsItem[]> {
  return get(`/news?limit=${limit}`);
}

export function fetchNewsByTicker(ticker: string, limit = 20): Promise<NewsItem[]> {
  return get(`/news/${encodeURIComponent(ticker)}?limit=${limit}`);
}

export async function updateCompany(id: number, req: CompanyUpdateRequest): Promise<Company> {
  const res = await fetch(`${BASE}/companies/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export async function deleteCompany(id: number): Promise<void> {
  const res = await fetch(`${BASE}/companies/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
}

export function lookupCompany(ticker: string): Promise<CompanyLookupResult> {
  return get(`/companies/lookup?ticker=${encodeURIComponent(ticker.trim().toUpperCase())}`);
}

export async function addCompany(req: CompanyAddRequest): Promise<CompanyAddResponse> {
  const res = await fetch(`${BASE}/companies/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

export interface MissingDataStub {
  id: number;
  name: string;
  ticker: string | null;
  country: string | null;
}

export interface MissingDataResult {
  missing_website: MissingDataStub[];
  missing_industry: MissingDataStub[];
  missing_revenue: MissingDataStub[];
  missing_all: MissingDataStub[];
}

export function fetchMissingData(): Promise<MissingDataResult> {
  return get("/companies/missing-data");
}

export function fetchEvents(params: { event_type?: EventType; company_id?: number; limit?: number } = {}): Promise<EventWithCompany[]> {
  const q = new URLSearchParams();
  if (params.event_type) q.set("event_type", params.event_type);
  if (params.company_id) q.set("company_id", String(params.company_id));
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return get(`/events${qs ? `?${qs}` : ""}`);
}
