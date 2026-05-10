import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchTerritoryRollup, fetchCompanies } from "../api/client";
import type { TerritoryRollup, Company, CompanyStatus } from "../types";
import { formatCap, formatPrice } from "../components/FormatCap";

// ── Sort types ──────────────────────────────────────────────────────────────

type SortCol =
  | "name" | "ticker" | "country" | "supply_chain_position"
  | "latest_price" | "latest_revenue" | "latest_market_cap" | "status";

interface SortDef { col: SortCol; dir: "asc" | "desc" }
interface SortState { primary: SortDef; secondary?: SortDef }

const TEXT_COLS = new Set<SortCol>(["name", "ticker", "country", "supply_chain_position", "status"]);
const ASC_DEFAULT = new Set<SortCol>(["name", "ticker"]);

function defaultDir(col: SortCol): "asc" | "desc" {
  return ASC_DEFAULT.has(col) ? "asc" : "desc";
}

function getValue(c: Company, col: SortCol): string | number | null {
  switch (col) {
    case "name":                 return c.name;
    case "ticker":               return c.ticker ?? null;
    case "country":              return c.country ?? null;
    case "supply_chain_position":return c.supply_chain_position ?? null;
    case "status":               return c.status ?? null;
    case "latest_price":         return c.latest_price ?? null;
    case "latest_revenue":       return c.latest_revenue ?? null;
    case "latest_market_cap":    return c.latest_market_cap ?? null;
  }
}

function compareByCol(a: Company, b: Company, col: SortCol, dir: "asc" | "desc"): number {
  const va = getValue(a, col);
  const vb = getValue(b, col);
  if (va === null && vb === null) return 0;
  if (va === null) return 1;   // nulls always to bottom
  if (vb === null) return -1;
  let cmp: number;
  if (TEXT_COLS.has(col)) {
    cmp = String(va).localeCompare(String(vb));
  } else {
    cmp = (va as number) - (vb as number);
  }
  return dir === "asc" ? cmp : -cmp;
}

function sortCompanies(companies: Company[], state: SortState): Company[] {
  return [...companies].sort((a, b) => {
    const p = compareByCol(a, b, state.primary.col, state.primary.dir);
    if (p !== 0) return p;
    if (state.secondary) return compareByCol(a, b, state.secondary.col, state.secondary.dir);
    return 0;
  });
}

// ── SortTh ──────────────────────────────────────────────────────────────────

interface SortThProps {
  col: SortCol;
  label: string;
  right?: boolean;
  sortState: SortState;
  onSort: (col: SortCol, e: React.MouseEvent<HTMLTableCellElement>) => void;
}

function SortTh({ col, label, right, sortState, onSort }: SortThProps) {
  const isPrimary   = sortState.primary.col === col;
  const isSecondary = sortState.secondary?.col === col;
  const active = isPrimary || isSecondary;
  const dir    = isPrimary ? sortState.primary.dir : sortState.secondary?.dir;

  return (
    <th
      onClick={(e) => onSort(col, e)}
      title={`Sort by ${label}\nShift+click to add as secondary sort`}
      style={{
        cursor: "pointer", userSelect: "none", whiteSpace: "nowrap",
        textAlign: right ? "right" : "left",
        color: active ? "#2563eb" : undefined,
      }}
    >
      <span style={{ fontWeight: active ? 700 : undefined }}>{label}</span>
      <span style={{
        marginLeft: 5, fontSize: 11,
        color: active ? "#2563eb" : "#9ca3af",
        position: "relative", display: "inline-block",
      }}>
        {active ? (dir === "asc" ? "▲" : "▼") : "↕"}
        {isSecondary && (
          <span style={{
            position: "absolute", top: -5, right: -9,
            fontSize: 8, fontWeight: 700, color: "#fff",
            background: "#2563eb", borderRadius: "50%",
            width: 10, height: 10,
            display: "inline-flex", alignItems: "center", justifyContent: "center",
          }}>2</span>
        )}
      </span>
    </th>
  );
}

// ── Status badge ─────────────────────────────────────────────────────────────

const STATUS_BADGE_STYLE: Record<string, { background: string; color: string }> = {
  Acquired:     { background: "#fef2f2", color: "#dc2626" },
  Merged:       { background: "#fff7ed", color: "#ea580c" },
  Delisted:     { background: "#f3f4f6", color: "#6b7280" },
  Sanctioned:   { background: "#f5f3ff", color: "#7c3aed" },
  "Non-Equity": { background: "#f0fdf4", color: "#16a34a" },
  Unknown:      { background: "#f3f4f6", color: "#9ca3af" },
};

function StatusBadge({ status }: { status?: CompanyStatus | string }) {
  if (!status || status === "Active") return null;
  const s = STATUS_BADGE_STYLE[status] ?? STATUS_BADGE_STYLE.Unknown;
  return <span className="status-badge" style={s}>{status.toUpperCase()}</span>;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const INACTIVE_STATUSES = new Set(["Acquired", "Merged", "Delisted", "Non-Equity"]);
const TABLE_PAGE_SIZE   = 50;
const SORT_SS_KEY       = (n: string) => `td-sort-${n}`;

function loadSortState(name: string): SortState {
  try {
    const s = sessionStorage.getItem(SORT_SS_KEY(name));
    if (s) return JSON.parse(s) as SortState;
  } catch { /* ignore */ }
  return { primary: { col: "latest_market_cap", dir: "desc" } };
}

// ── Overview ──────────────────────────────────────────────────────────────────

function OverviewView({
  rows, loading, error,
}: {
  rows: TerritoryRollup[]; loading: boolean; error: string | null;
}) {
  const navigate = useNavigate();
  const maxCap = rows.reduce((m, r) => Math.max(m, r.total_market_cap_usd ?? 0), 0);
  const totalCap = rows.reduce((s, r) => s + (r.total_market_cap_usd ?? 0), 0);
  const totalRev = rows.reduce((s, r) => s + (r.total_revenue_usd ?? 0), 0);
  const totalCompanies = rows.reduce((s, r) => s + r.company_count, 0);

  return (
    <>
      <div className="page-header">
        <h1>Territory Dashboard</h1>
      </div>
      <div className="page-body">
        {error && <div className="error">{error}</div>}
        {loading ? (
          <div className="loading">Loading...</div>
        ) : (
          <>
            <div className="stat-grid">
              <div className="stat-card">
                <div className="label">Total Market Cap</div>
                <div className="value">{formatCap(totalCap)}</div>
                <div className="sub">across all territories</div>
              </div>
              <div className="stat-card">
                <div className="label">Total Revenue</div>
                <div className="value">{formatCap(totalRev)}</div>
                <div className="sub">annual, all territories</div>
              </div>
              <div className="stat-card">
                <div className="label">Companies Tracked</div>
                <div className="value">{totalCompanies.toLocaleString()}</div>
              </div>
              <div className="stat-card">
                <div className="label">Territories</div>
                <div className="value">{rows.length}</div>
              </div>
            </div>

            <div className="card">
              <table>
                <thead>
                  <tr>
                    <th>WWT Territory</th>
                    <th style={{ textAlign: "right" }}>Companies</th>
                    <th style={{ textAlign: "right" }}>Total Market Cap</th>
                    <th style={{ textAlign: "right" }}>Total Revenue</th>
                    <th style={{ width: 200 }}>Share of Market Cap</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const pct = maxCap > 0 ? ((r.total_market_cap_usd ?? 0) / maxCap) * 100 : 0;
                    return (
                      <tr key={r.wwt_territory}>
                        <td>
                          <button
                            onClick={() => navigate(`/territories/${encodeURIComponent(r.wwt_territory)}`)}
                            style={{
                              background: "none", border: "none", cursor: "pointer",
                              fontWeight: 700, color: "#2563eb", fontSize: 14, padding: 0,
                              textDecoration: "underline",
                              textDecorationColor: "rgba(37,99,235,0.4)",
                            }}
                          >
                            {r.wwt_territory}
                          </button>
                        </td>
                        <td style={{ textAlign: "right" }}>{r.company_count}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {formatCap(r.total_market_cap_usd)}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                          {formatCap(r.total_revenue_usd)}
                        </td>
                        <td>
                          <div className="territory-bar">
                            <div className="territory-bar-fill" style={{ width: `${pct}%` }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

// ── Detail (drill-down) ───────────────────────────────────────────────────────

function DetailView({ name }: { name: string }) {
  const navigate = useNavigate();
  const [companies, setCompanies]   = useState<Company[]>([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [page, setPage]             = useState(1);
  const [sortState, setSortState]   = useState<SortState>(() => loadSortState(name));
  const [nameSearch, setNameSearch] = useState("");

  // Browser tab title
  useEffect(() => {
    document.title = `${name} — Energy Tracker`;
    return () => { document.title = "Energy Tracker"; };
  }, [name]);

  // Persist sort
  useEffect(() => {
    sessionStorage.setItem(SORT_SS_KEY(name), JSON.stringify(sortState));
  }, [name, sortState]);

  // Load all companies for this territory (all statuses, no server-side sort needed)
  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchCompanies({
      wwt_territory: name,
      status: "all",
      sort_by: "name",
      sort_dir: "asc",
      page: 1,
      page_size: 500,
    })
      .then(d => { setCompanies(d.items); setTotal(d.total); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [name]);

  // Client-side sort then name filter
  const sorted = useMemo(() => sortCompanies(companies, sortState), [companies, sortState]);
  const nameFiltered = useMemo(() => {
    if (!nameSearch.trim()) return sorted;
    const q = nameSearch.toLowerCase();
    return sorted.filter(c => c.name.toLowerCase().includes(q));
  }, [sorted, nameSearch]);

  // Client-side pagination
  const pageCount = Math.ceil(nameFiltered.length / TABLE_PAGE_SIZE);
  const pageItems = nameFiltered.slice((page - 1) * TABLE_PAGE_SIZE, page * TABLE_PAGE_SIZE);

  // Aggregate metrics
  const totalCap = useMemo(
    () => companies.reduce((s, c) => s + (c.latest_market_cap ?? 0), 0),
    [companies]
  );
  const totalRev = useMemo(
    () => companies.reduce((s, c) => s + (c.latest_revenue ?? 0), 0),
    [companies]
  );

  function handleSort(col: SortCol, e: React.MouseEvent<HTMLTableCellElement>) {
    setSortState(prev => {
      if (e.shiftKey) {
        if (prev.primary.col === col) return prev; // can't be both
        if (prev.secondary?.col === col) {
          return {
            ...prev,
            secondary: { col, dir: prev.secondary.dir === "asc" ? "desc" : "asc" },
          };
        }
        return { ...prev, secondary: { col, dir: defaultDir(col) } };
      }
      // Normal click — set primary, clear secondary
      if (prev.primary.col === col) {
        return { primary: { col, dir: prev.primary.dir === "asc" ? "desc" : "asc" } };
      }
      return { primary: { col, dir: defaultDir(col) } };
    });
    setPage(1);
  }

  const thProps = { sortState, onSort: handleSort };

  const anyFilterActive = !!nameSearch.trim();
  const selectStyle: React.CSSProperties = {
    padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
    fontSize: 13, background: "#fff", color: "#1a1a2e", cursor: "pointer",
  };

  return (
    <>
      {/* Fixed filter bar — matches Analytics */}
      <div style={{
        position: "fixed", top: 0, left: 220, right: 0, zIndex: 200,
        background: "#1a1a2e", borderBottom: "1px solid rgba(255,255,255,0.1)",
        padding: "10px 28px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
      }}>
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginRight: 8, whiteSpace: "nowrap" }}>Filters</span>
        <input
          type="search" placeholder="Search company name…" value={nameSearch}
          onChange={e => { setNameSearch(e.target.value); setPage(1); }}
          style={{ ...selectStyle, minWidth: 200 }}
        />
        {anyFilterActive && (
          <button onClick={() => { setNameSearch(""); setPage(1); }} style={{
            padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
            fontSize: 13, background: "#fff", color: "#6b7280", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap",
          }}>
            ↺ Reset
          </button>
        )}
      </div>

      <div className="page-header" style={{ justifyContent: "space-between", paddingTop: 56 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button className="back-btn" onClick={() => navigate("/territories")}>
            ← All Territories
          </button>
          <h1>{name} — {nameFiltered.length.toLocaleString()} companies</h1>
        </div>
      </div>

      <div className="page-body">
        {error && <div className="error">{error}</div>}

        {!loading && (
          <>
            <div className="stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              <div className="stat-card">
                <div className="label">Total Companies</div>
                <div className="value">{total.toLocaleString()}</div>
              </div>
              <div className="stat-card">
                <div className="label">Combined Market Cap</div>
                <div className="value">{totalCap > 0 ? formatCap(totalCap) : "—"}</div>
              </div>
              <div className="stat-card">
                <div className="label">Combined Revenue</div>
                <div className="value">{totalRev > 0 ? formatCap(totalRev) : "—"}</div>
                <div className="sub">annual FY, companies with data</div>
              </div>
            </div>

            <div className="card" style={{ padding: 0 }}>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <SortTh col="name"                  label="Company"            {...thProps} />
                      <SortTh col="ticker"                label="Ticker"             {...thProps} />
                      <SortTh col="country"               label="Country"            {...thProps} />
                      <SortTh col="supply_chain_position" label="Energy Value Chain" {...thProps} />
                      <SortTh col="latest_price"          label="Price"    right     {...thProps} />
                      <SortTh col="latest_revenue"        label="FY Rev"   right     {...thProps} />
                      <SortTh col="latest_market_cap"     label="Market Cap" right   {...thProps} />
                      <SortTh col="status"                label="Status"             {...thProps} />
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.length === 0 ? (
                      <tr>
                        <td colSpan={8} style={{ textAlign: "center", padding: "32px", color: "#9ca3af" }}>
                          No companies in this territory.
                        </td>
                      </tr>
                    ) : pageItems.map(c => {
                      const isInactive = INACTIVE_STATUSES.has(c.status ?? "");
                      return (
                        <tr key={c.id} className={isInactive ? "row-inactive" : ""}>
                          <td>
                            <Link
                              to={c.ticker ? `/company/${c.ticker}` : `/companies/${c.id}`}
                              style={{ fontWeight: 500 }}
                            >
                              {c.name}
                            </Link>
                          </td>
                          <td style={{ fontFamily: "monospace", color: "#6b7280" }}>
                            {c.ticker ?? "—"}
                          </td>
                          <td>{c.country ?? "—"}</td>
                          <td>
                            {c.supply_chain_position
                              ? <span className="badge badge-supply-chain">{c.supply_chain_position}</span>
                              : "—"}
                          </td>
                          <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                            {formatPrice(c.latest_price)}
                          </td>
                          <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#6b7280" }}>
                            {c.latest_revenue
                              ? `${formatCap(c.latest_revenue)}${c.latest_fiscal_year_label ? ` ${c.latest_fiscal_year_label}` : ""}`
                              : "—"}
                          </td>
                          <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                            {formatCap(c.latest_market_cap)}
                          </td>
                          <td>
                            <StatusBadge status={c.status} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {pageCount > 1 && (
              <div className="pagination">
                <button onClick={() => setPage(1)} disabled={page === 1}>«</button>
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>‹</button>
                <span>Page {page} of {pageCount}</span>
                <button onClick={() => setPage(p => Math.min(pageCount, p + 1))} disabled={page === pageCount}>›</button>
                <button onClick={() => setPage(pageCount)} disabled={page === pageCount}>»</button>
              </div>
            )}
          </>
        )}

        {loading && <div className="loading">Loading...</div>}
      </div>
    </>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function TerritoryDashboard() {
  const { name } = useParams<{ name?: string }>();
  const [rollupRows, setRollupRows]   = useState<TerritoryRollup[]>([]);
  const [rollupLoading, setLoading]   = useState(true);
  const [rollupError, setError]       = useState<string | null>(null);

  useEffect(() => {
    fetchTerritoryRollup()
      .then(setRollupRows)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (name) {
    return <DetailView name={decodeURIComponent(name)} />;
  }

  return <OverviewView rows={rollupRows} loading={rollupLoading} error={rollupError} />;
}
