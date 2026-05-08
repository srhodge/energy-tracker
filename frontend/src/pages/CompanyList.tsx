import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { fetchCompanies, fetchFilterOptions, fetchStatusSummary } from "../api/client";
import type { Company, FilterOptions, StatusSummary, EnergySegment, ValueChainPosition, CompanyStatus } from "../types";
import { formatCap, formatPrice } from "../components/FormatCap";
import SupplyChainChart from "../components/SupplyChainChart";

const PAGE_SIZE = 50;

const STATUS_BADGE_STYLE: Record<string, { background: string; color: string }> = {
  Acquired:    { background: "#fef2f2", color: "#dc2626" },
  Merged:      { background: "#fff7ed", color: "#ea580c" },
  Delisted:    { background: "#f3f4f6", color: "#6b7280" },
  Sanctioned:  { background: "#f5f3ff", color: "#7c3aed" },
  "Non-Equity":{ background: "#f0fdf4", color: "#16a34a" },
  Unknown:     { background: "#f3f4f6", color: "#9ca3af" },
};

function StatusBadge({ status }: { status?: CompanyStatus }) {
  if (!status || status === "Active") return null;
  const s = STATUS_BADGE_STYLE[status] ?? STATUS_BADGE_STYLE.Unknown;
  return <span className="status-badge" style={s}>{status.toUpperCase()}</span>;
}

function StatusSummaryBar({ summary }: { summary: StatusSummary }) {
  const items: { label: string; key: keyof StatusSummary; color: string }[] = [
    { label: "Active",     key: "Active",     color: "#16a34a" },
    { label: "Unknown",    key: "Unknown",    color: "#9ca3af" },
    { label: "Sanctioned", key: "Sanctioned", color: "#7c3aed" },
    { label: "Acquired",   key: "Acquired",   color: "#dc2626" },
    { label: "Merged",     key: "Merged",     color: "#ea580c" },
    { label: "Delisted",   key: "Delisted",   color: "#6b7280" },
  ];
  return (
    <div className="status-summary-bar">
      {items.map(({ label, key, color }) => (
        summary[key] > 0 && (
          <span key={key} className="status-summary-item" style={{ color }}>
            <span className="status-summary-dot" style={{ background: color }} />
            {label} <strong>{summary[key]}</strong>
          </span>
        )
      ))}
    </div>
  );
}

const INACTIVE_STATUSES: CompanyStatus[] = ["Acquired", "Merged", "Delisted", "Non-Equity"];

export default function CompanyList() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [statusSummary, setStatusSummary] = useState<StatusSummary | null>(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [territory, setTerritory] = useState("");
  const [segment, setSegment] = useState("");
  const [chainPos, setChainPos] = useState("");
  const [supplyChain, setSupplyChain] = useState("");
  const [country, setCountry] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);

  useEffect(() => {
    fetchFilterOptions().then(setFilters).catch(() => null);
    fetchStatusSummary().then(setStatusSummary).catch(() => null);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchCompanies({
      search: search || undefined,
      wwt_territory: territory || undefined,
      energy_segment: (segment as EnergySegment) || undefined,
      value_chain_position: (chainPos as ValueChainPosition) || undefined,
      supply_chain_position: supplyChain || undefined,
      country: country || undefined,
      include_inactive: includeInactive || undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setCompanies(data.items);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search, territory, segment, chainPos, supplyChain, country, includeInactive, page]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleFilterChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  return (
    <>
      <div className="page-header">
        <h1>Companies</h1>
        <span style={{ color: "#6b7280", fontSize: 13 }}>{total.toLocaleString()} companies</span>
      </div>
      <div className="page-body">
        <SupplyChainChart />

        {statusSummary && <StatusSummaryBar summary={statusSummary} />}

        <div className="filter-bar">
          <input
            type="search"
            placeholder="Search company name..."
            value={search}
            onChange={handleFilterChange(setSearch)}
          />
          <select value={territory} onChange={handleFilterChange(setTerritory)}>
            <option value="">All territories</option>
            {filters?.wwt_territories.map((t) => <option key={t}>{t}</option>)}
          </select>
          <select value={segment} onChange={handleFilterChange(setSegment)}>
            <option value="">All segments</option>
            {filters?.energy_segments.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={chainPos} onChange={handleFilterChange(setChainPos)}>
            <option value="">All value chain positions</option>
            {filters?.value_chain_positions.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select value={supplyChain} onChange={handleFilterChange(setSupplyChain)}>
            <option value="">All supply chain positions</option>
            {filters?.supply_chain_positions.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select value={country} onChange={handleFilterChange(setCountry)}>
            <option value="">All countries</option>
            {filters?.countries.map((c) => <option key={c}>{c}</option>)}
          </select>
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={includeInactive}
              onChange={(e) => { setIncludeInactive(e.target.checked); setPage(1); }}
            />
            Show acquired &amp; inactive
          </label>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            {loading ? (
              <div className="loading">Loading...</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Ticker</th>
                    <th>Territory</th>
                    <th>Segment</th>
                    <th>Supply Chain</th>
                    <th>Country</th>
                    <th style={{ textAlign: "right" }}>Market Cap</th>
                    <th style={{ textAlign: "right" }}>Price</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ textAlign: "center", padding: "32px", color: "#9ca3af" }}>
                        No companies match the current filters.
                      </td>
                    </tr>
                  ) : companies.map((c) => {
                    const isInactive = INACTIVE_STATUSES.includes(c.status as CompanyStatus);
                    return (
                      <tr key={c.id} className={isInactive ? "row-inactive" : ""}>
                        <td>
                          <Link
                            to={c.ticker ? `/company/${c.ticker}` : `/companies/${c.id}`}
                            style={{ fontWeight: 500 }}
                          >
                            {c.name}
                          </Link>
                          {" "}
                          <StatusBadge status={c.status} />
                        </td>
                        <td style={{ fontFamily: "monospace", color: "#6b7280" }}>{c.ticker ?? "—"}</td>
                        <td>{c.wwt_territory ? <span className="badge badge-territory">{c.wwt_territory}</span> : "—"}</td>
                        <td>{c.energy_segment ? <span className="badge badge-segment">{c.energy_segment}</span> : "—"}</td>
                        <td>{c.supply_chain_position ? <span className="badge badge-supply-chain">{c.supply_chain_position}</span> : "—"}</td>
                        <td>{c.country ?? "—"}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCap(c.latest_market_cap)}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatPrice(c.latest_price)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <button onClick={() => setPage(1)} disabled={page === 1}>«</button>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>‹</button>
            <span>Page {page} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>›</button>
            <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>»</button>
          </div>
        )}
      </div>
    </>
  );
}
