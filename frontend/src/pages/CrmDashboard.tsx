import { useEffect, useState, useMemo } from "react";
import {
  fetchCrmSummary, fetchCrmCompanies, fetchCrmCompany,
  fetchCrmOpportunities, fetchCrmOwners, fetchCrmFilterOptions,
} from "../api/client";

// ── Constants ─────────────────────────────────────────────────────────────────

const MY_TEAM = new Set(["Sam Hodge", "Matthew Nalbone", "Shay Gillespie"]);

const NUMERIC_SORT_COLS = new Set<CompanySortCol>(
  ["open_pipeline", "closed_won", "closed_lost", "total_deals", "win_rate"]
);

// ── Shared filter bar styles (match Analytics exactly) ────────────────────────

const FILTER_BAR: React.CSSProperties = {
  position: "fixed", top: 0, left: 220, right: 0, zIndex: 200,
  background: "#1a1a2e",
  borderBottom: "1px solid rgba(255,255,255,0.1)",
  padding: "10px 28px",
  display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
};

const SEL: React.CSSProperties = {
  padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
  fontSize: 13, background: "#fff", color: "#1a1a2e", cursor: "pointer",
};

const SEL_ACTIVE: React.CSSProperties = {
  ...SEL, background: "#eff6ff", color: "#1d4ed8",
  border: "1.5px solid #2563eb", fontWeight: 700,
};

const RESET_BTN: React.CSSProperties = {
  padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
  fontSize: 13, background: "#fff", color: "#6b7280", cursor: "pointer",
  display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap",
};

const FILTER_LABEL: React.CSSProperties = {
  fontSize: 12, color: "rgba(255,255,255,0.5)", marginRight: 8, whiteSpace: "nowrap",
};

// ── Types ─────────────────────────────────────────────────────────────────────

type Tab = "summary" | "companies" | "opportunities" | "owners";
type CompanySortCol = "name" | "open_pipeline" | "closed_won" | "closed_lost" | "total_deals" | "win_rate" | "latest_close_date";
type CompanyViewFilter = "all" | "has_deals" | "active_pipeline";

interface FilterOpts { stages: string[]; owners: string[]; fiscal_periods: string[]; }

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "—";
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function pct(v: number): string { return `${(v * 100).toFixed(1)}%`; }

function stageBadgeStyle(stage: string | null): React.CSSProperties {
  const s = (stage || "").toLowerCase();
  if (s === "closed won")   return { background: "#dcfce7", color: "#15803d" };
  if (s.includes("closed")) return { background: "#fee2e2", color: "#dc2626" };
  return { background: "#eff6ff", color: "#2563eb" };
}

const PAGE_SIZE = 50;

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

// ── SortTh ────────────────────────────────────────────────────────────────────

function SortTh({
  col, children, right, sortCol, sortDir, onSort,
}: {
  col: CompanySortCol; children: React.ReactNode; right?: boolean;
  sortCol: CompanySortCol; sortDir: "asc" | "desc"; onSort: (col: CompanySortCol) => void;
}) {
  const active = sortCol === col;
  return (
    <th onClick={() => onSort(col)} style={{
      cursor: "pointer", userSelect: "none", whiteSpace: "nowrap",
      textAlign: right ? "right" : "left",
      color: active ? "#2563eb" : undefined,
    }}>
      <span style={{ fontWeight: active ? 700 : undefined }}>{children}</span>
      <span style={{ marginLeft: 5, fontSize: 11, color: active ? "#2563eb" : "#9ca3af" }}>
        {active ? (sortDir === "asc" ? "▲" : "▼") : "↕"}
      </span>
    </th>
  );
}

// ── Summary tab ───────────────────────────────────────────────────────────────

function SummaryTab() {
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchCrmSummary().then(setData).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="loading">Loading…</div>;
  if (!data)   return <div className="error">Failed to load summary.</div>;

  return (
    <>
      <div className="stat-grid">
        <StatCard label="Open Pipeline" value={fmt(data.open_pipeline)} />
        <StatCard label="Closed Won"    value={fmt(data.closed_won)} />
        <StatCard label="Win Rate"      value={pct(data.win_rate)} sub="closed won ÷ decided" />
        <StatCard label="Avg Deal Size" value={fmt(data.avg_deal_size)} sub="closed won deals" />
        <StatCard label="Total Deals"   value={data.total_opportunities.toLocaleString()} />
        <StatCard label="Accounts"      value={data.total_accounts.toLocaleString()} />
      </div>
      <div className="card">
        <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#374151" }}>Pipeline by Stage</h3>
        <table>
          <thead>
            <tr>
              <th>Stage</th>
              <th style={{ textAlign: "right" }}>Deals</th>
              <th style={{ textAlign: "right" }}>Total Amount</th>
            </tr>
          </thead>
          <tbody>
            {data.by_stage.map((s: any) => (
              <tr key={s.stage}>
                <td>
                  <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 12, fontWeight: 500, ...stageBadgeStyle(s.stage) }}>
                    {s.stage}
                  </span>
                </td>
                <td style={{ textAlign: "right" }}>{s.count.toLocaleString()}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(s.total_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Companies tab ─────────────────────────────────────────────────────────────

interface CompaniesTabProps {
  onDrillDown: (id: number, name: string) => void;
  search: string;
  viewFilter: CompanyViewFilter;
  sortCol: CompanySortCol;
  sortDir: "asc" | "desc";
  onSort: (col: CompanySortCol) => void;
}

function CompaniesTab({ onDrillDown, search, viewFilter, sortCol, sortDir, onSort }: CompaniesTabProps) {
  const [allRows, setAllRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCrmCompanies().then(setAllRows).finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let rows = allRows;
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(r => r.name.toLowerCase().includes(q));
    }
    if (viewFilter === "has_deals")       rows = rows.filter(r => r.total_deals > 0);
    if (viewFilter === "active_pipeline") rows = rows.filter(r => (r.open_pipeline ?? 0) > 0);
    return [...rows].sort((a, b) => {
      const va = a[sortCol] ?? (NUMERIC_SORT_COLS.has(sortCol) ? 0 : "");
      const vb = b[sortCol] ?? (NUMERIC_SORT_COLS.has(sortCol) ? 0 : "");
      const cmp = NUMERIC_SORT_COLS.has(sortCol)
        ? (va as number) - (vb as number)
        : String(va).localeCompare(String(vb));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [allRows, search, viewFilter, sortCol, sortDir]);

  if (loading) return <div className="loading">Loading…</div>;

  const thProps = { sortCol, sortDir, onSort };

  return (
    <>
      <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>
        {filtered.length.toLocaleString()} accounts
      </div>
      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh col="name" {...thProps}>Account</SortTh>
                <SortTh col="total_deals" right {...thProps}>Total Deals</SortTh>
                <SortTh col="open_pipeline" right {...thProps}>Open Pipeline</SortTh>
                <SortTh col="closed_won" right {...thProps}>Closed Won</SortTh>
                <SortTh col="closed_lost" right {...thProps}>Closed Lost</SortTh>
                <SortTh col="win_rate" right {...thProps}>Win Rate</SortTh>
                <SortTh col="latest_close_date" right {...thProps}>Latest Close</SortTh>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: "32px", color: "#9ca3af" }}>No accounts match.</td></tr>
              ) : filtered.map((r: any) => {
                const isEmpty = (r.open_pipeline ?? 0) === 0 && (r.closed_won ?? 0) === 0 && (r.closed_lost ?? 0) === 0;
                return (
                  <tr key={r.id} style={{ opacity: isEmpty ? 0.38 : 1 }}>
                    <td>
                      <button onClick={() => onDrillDown(r.id, r.name)} style={{
                        background: "none", border: "none", cursor: "pointer",
                        fontWeight: 600, color: isEmpty ? "#6b7280" : "#2563eb",
                        fontSize: 14, padding: 0,
                        textDecoration: isEmpty ? "none" : "underline",
                        textDecorationColor: "rgba(37,99,235,0.4)",
                      }}>
                        {r.name}
                      </button>
                    </td>
                    <td style={{ textAlign: "right" }}>{r.total_deals}</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(r.open_pipeline)}</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: isEmpty ? undefined : "#15803d" }}>{fmt(r.closed_won)}</td>
                    <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: isEmpty ? undefined : "#dc2626" }}>{fmt(r.closed_lost)}</td>
                    <td style={{ textAlign: "right" }}>{pct(r.win_rate)}</td>
                    <td style={{ textAlign: "right", color: "#6b7280", fontSize: 13 }}>{r.latest_close_date ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ── Company detail (drill-down) ───────────────────────────────────────────────

function CompanyDetail({ id, name, onBack }: { id: number; name: string; onBack: () => void }) {
  const [data, setData]             = useState<any>(null);
  const [loading, setLoading]       = useState(true);
  const [stageFilter, setStageFilter] = useState("");

  useEffect(() => { fetchCrmCompany(id).then(setData).finally(() => setLoading(false)); }, [id]);

  const stages = useMemo(() => {
    if (!data) return [];
    return Array.from(new Set<string>(data.opportunities.map((o: any) => o.stage).filter(Boolean))).sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return stageFilter ? data.opportunities.filter((o: any) => o.stage === stageFilter) : data.opportunities;
  }, [data, stageFilter]);

  if (loading) return <div className="loading">Loading…</div>;
  if (!data)   return <div className="error">Not found.</div>;

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <button className="back-btn" onClick={onBack}>← All Accounts</button>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700 }}>{name}</h2>
      </div>
      <div className="stat-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 16 }}>
        <StatCard label="Total Deals"   value={data.total_deals.toLocaleString()} />
        <StatCard label="Open Pipeline" value={fmt(data.open_pipeline)} />
        <StatCard label="Closed Won"    value={fmt(data.closed_won)} />
        <StatCard label="Win Rate"      value={pct(data.win_rate)} />
      </div>
      <div style={{ marginBottom: 12 }}>
        <select value={stageFilter} onChange={e => setStageFilter(e.target.value)} style={SEL}>
          <option value="">All Stages</option>
          {stages.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Opportunity</th><th>Owner</th><th>Stage</th>
                <th>Fiscal Period</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th style={{ textAlign: "right" }}>Close Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: 32, color: "#9ca3af" }}>No opportunities.</td></tr>
              ) : filtered.map((o: any) => (
                <tr key={o.id}>
                  <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.opportunity_name}</td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.opportunity_owner ?? "—"}</td>
                  <td>
                    <span style={{ display: "inline-block", padding: "2px 7px", borderRadius: 4, fontSize: 11, fontWeight: 500, ...stageBadgeStyle(o.stage) }}>
                      {o.stage}
                    </span>
                  </td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.fiscal_period ?? "—"}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(o.amount)}</td>
                  <td style={{ textAlign: "right", color: "#6b7280", fontSize: 13 }}>{o.close_date ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ── Opportunities tab ─────────────────────────────────────────────────────────

interface OpportunitiesTabProps {
  stageFilter: string; ownerFilter: string; periodFilter: string;
  accountSearch: string; activeOnly: boolean;
  page: number; setPage: (p: number | ((prev: number) => number)) => void;
}

function OpportunitiesTab({
  stageFilter, ownerFilter, periodFilter, accountSearch, activeOnly, page, setPage,
}: OpportunitiesTabProps) {
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchCrmOpportunities({
      stage:         stageFilter    || undefined,
      owner:         ownerFilter    || undefined,
      fiscal_period: periodFilter   || undefined,
      account_name:  accountSearch.trim() || undefined,
      active_only:   activeOnly     || undefined,
      page, page_size: PAGE_SIZE,
    }).then(setData).finally(() => setLoading(false));
  }, [stageFilter, ownerFilter, periodFilter, accountSearch, activeOnly, page]);

  const pageCount = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  return (
    <>
      {data && (
        <div style={{ fontSize: 13, color: "#6b7280", marginBottom: 8 }}>
          {data.total.toLocaleString()} opportunities
        </div>
      )}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Opportunity</th><th>Account</th><th>Owner</th>
                <th>Stage</th><th>Fiscal Period</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th style={{ textAlign: "right" }}>Close Date</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: 32, color: "#9ca3af" }}>Loading…</td></tr>
              ) : !data?.items?.length ? (
                <tr><td colSpan={7} style={{ textAlign: "center", padding: 32, color: "#9ca3af" }}>No results.</td></tr>
              ) : data.items.map((o: any) => (
                <tr key={o.id}>
                  <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{o.opportunity_name}</td>
                  <td style={{ color: "#374151", fontSize: 13 }}>{o.account_name ?? "—"}</td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.opportunity_owner ?? "—"}</td>
                  <td>
                    <span style={{ display: "inline-block", padding: "2px 7px", borderRadius: 4, fontSize: 11, fontWeight: 500, ...stageBadgeStyle(o.stage) }}>
                      {o.stage}
                    </span>
                  </td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.fiscal_period ?? "—"}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(o.amount)}</td>
                  <td style={{ textAlign: "right", color: "#6b7280", fontSize: 13 }}>{o.close_date ?? "—"}</td>
                </tr>
              ))}
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
  );
}

// ── Owners tab ────────────────────────────────────────────────────────────────

function OwnersTab({ myTeamOnly }: { myTeamOnly: boolean }) {
  const [allRows, setAllRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchCrmOwners().then(setAllRows).finally(() => setLoading(false)); }, []);

  if (loading) return <div className="loading">Loading…</div>;

  const teamRows  = allRows.filter(r => MY_TEAM.has(r.opportunity_owner));
  const otherRows = allRows.filter(r => !MY_TEAM.has(r.opportunity_owner));
  const displayed = myTeamOnly ? teamRows : [...teamRows, ...otherRows];

  return (
    <div className="card" style={{ padding: 0 }}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Owner</th>
              <th style={{ textAlign: "right" }}>Total Deals</th>
              <th style={{ textAlign: "right" }}>Open Pipeline</th>
              <th style={{ textAlign: "right" }}>Closed Won</th>
              <th style={{ textAlign: "right" }}>Closed Lost</th>
              <th style={{ textAlign: "right" }}>Win Rate</th>
              <th style={{ textAlign: "right" }}>Avg Deal Size</th>
            </tr>
          </thead>
          <tbody>
            {displayed.map((r: any, i: number) => {
              const isTeam = MY_TEAM.has(r.opportunity_owner);
              return (
                <tr key={r.opportunity_owner} style={{
                  background: isTeam ? "#eff6ff" : undefined,
                  borderLeft: isTeam ? "3px solid #2563eb" : "3px solid transparent",
                }}>
                  <td style={{ color: "#9ca3af", fontVariantNumeric: "tabular-nums", width: 32 }}>{i + 1}</td>
                  <td style={{ fontWeight: isTeam ? 700 : 600, color: isTeam ? "#1d4ed8" : undefined }}>
                    {r.opportunity_owner}
                    {isTeam && (
                      <span style={{ marginLeft: 8, fontSize: 11, background: "#dbeafe", color: "#1d4ed8", borderRadius: 4, padding: "1px 6px", fontWeight: 600 }}>
                        WWT
                      </span>
                    )}
                  </td>
                  <td style={{ textAlign: "right" }}>{r.total_deals.toLocaleString()}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(r.open_pipeline)}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#15803d" }}>{fmt(r.closed_won)}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#dc2626" }}>{fmt(r.closed_lost)}</td>
                  <td style={{ textAlign: "right" }}>{pct(r.win_rate)}</td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#6b7280" }}>{fmt(r.avg_deal_size)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function CrmDashboard() {
  const [tab, setTab]                   = useState<Tab>("summary");
  const [drillAccount, setDrillAccount] = useState<{ id: number; name: string } | null>(null);
  const [filterOpts, setFilterOpts]     = useState<FilterOpts | null>(null);

  // ── Companies filter state ────────────────────────────────────────────────
  const [cmpSearch,  setCmpSearch]  = useState("");
  const [cmpView,    setCmpView]    = useState<CompanyViewFilter>("all");
  const [cmpSortCol, setCmpSortCol] = useState<CompanySortCol>("open_pipeline");
  const [cmpSortDir, setCmpSortDir] = useState<"asc" | "desc">("desc");

  // ── Opportunities filter state ────────────────────────────────────────────
  const [oppStage,      setOppStage]      = useState("");
  const [oppOwner,      setOppOwner]      = useState("");
  const [oppPeriod,     setOppPeriod]     = useState("");
  const [oppAccount,    setOppAccount]    = useState("");
  const [oppActiveOnly, setOppActiveOnly] = useState(false);
  const [oppPage,       setOppPage]       = useState(1);

  // ── Owners filter state ───────────────────────────────────────────────────
  const [ownMyTeam, setOwnMyTeam] = useState(false);

  useEffect(() => { fetchCrmFilterOptions().then(setFilterOpts); }, []);

  // Reset opportunity page when any opp filter changes
  useEffect(() => { setOppPage(1); }, [oppStage, oppOwner, oppPeriod, oppAccount, oppActiveOnly]);

  // ── Sort handler for companies table ──────────────────────────────────────
  function handleCmpSort(col: CompanySortCol) {
    if (col === cmpSortCol) {
      setCmpSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setCmpSortCol(col);
      setCmpSortDir(NUMERIC_SORT_COLS.has(col) ? "desc" : "asc");
    }
  }

  // ── Reset helpers ─────────────────────────────────────────────────────────
  function resetCompanies() {
    setCmpSearch(""); setCmpView("all");
    setCmpSortCol("open_pipeline"); setCmpSortDir("desc");
  }
  function resetOpportunities() {
    setOppStage(""); setOppOwner(""); setOppPeriod("");
    setOppAccount(""); setOppActiveOnly(false); setOppPage(1);
  }
  function resetOwners() { setOwnMyTeam(false); }

  // ── Active filter checks ──────────────────────────────────────────────────
  const cmpAnyActive = !!(cmpSearch || cmpView !== "all" || cmpSortCol !== "open_pipeline" || cmpSortDir !== "desc");
  const oppAnyActive = !!(oppStage || oppOwner || oppPeriod || oppAccount || oppActiveOnly);
  const ownAnyActive = ownMyTeam;

  // ── Fixed filter bar ──────────────────────────────────────────────────────
  const showFilterBar = tab !== "summary" && !(tab === "companies" && drillAccount);

  function renderFilterBar() {
    if (!showFilterBar) return null;

    if (tab === "companies") {
      return (
        <div style={FILTER_BAR}>
          <span style={FILTER_LABEL}>Filters</span>
          <input
            type="search" placeholder="Search account…" value={cmpSearch}
            onChange={e => setCmpSearch(e.target.value)}
            style={{ ...SEL, minWidth: 200 }}
          />
          <select value={cmpView} onChange={e => setCmpView(e.target.value as CompanyViewFilter)} style={SEL}>
            <option value="all">All Accounts</option>
            <option value="has_deals">Has Deals</option>
            <option value="active_pipeline">Active Pipeline</option>
          </select>
          <select
            value={cmpSortCol}
            onChange={e => { const c = e.target.value as CompanySortCol; setCmpSortCol(c); setCmpSortDir(NUMERIC_SORT_COLS.has(c) ? "desc" : "asc"); }}
            style={SEL}
          >
            <option value="open_pipeline">Sort: Open Pipeline</option>
            <option value="closed_won">Sort: Closed Won</option>
            <option value="total_deals">Sort: Total Deals</option>
            <option value="win_rate">Sort: Win Rate</option>
            <option value="name">Sort: Account Name</option>
          </select>
          {cmpAnyActive && <button onClick={resetCompanies} style={RESET_BTN}>↺ Reset</button>}
        </div>
      );
    }

    if (tab === "opportunities") {
      return (
        <div style={FILTER_BAR}>
          <span style={FILTER_LABEL}>Filters</span>
          <input
            type="search" placeholder="Search account…" value={oppAccount}
            onChange={e => setOppAccount(e.target.value)}
            style={{ ...SEL, minWidth: 200 }}
          />
          <select value={oppStage} onChange={e => setOppStage(e.target.value)} style={SEL}>
            <option value="">All Stages</option>
            {filterOpts?.stages.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={oppOwner} onChange={e => setOppOwner(e.target.value)} style={SEL}>
            <option value="">All Owners</option>
            {filterOpts?.owners.map(o => <option key={o} value={o}>{o}</option>)}
          </select>
          <select value={oppPeriod} onChange={e => setOppPeriod(e.target.value)} style={SEL}>
            <option value="">All Fiscal Periods</option>
            {filterOpts?.fiscal_periods.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <button onClick={() => setOppActiveOnly(v => !v)} style={oppActiveOnly ? SEL_ACTIVE : SEL}>
            Active Only
          </button>
          {oppAnyActive && <button onClick={resetOpportunities} style={RESET_BTN}>↺ Reset</button>}
        </div>
      );
    }

    if (tab === "owners") {
      return (
        <div style={FILTER_BAR}>
          <span style={FILTER_LABEL}>Filters</span>
          <button onClick={() => setOwnMyTeam(v => !v)} style={ownMyTeam ? SEL_ACTIVE : SEL}>My Team</button>
          {ownAnyActive && <button onClick={resetOwners} style={RESET_BTN}>↺ Reset</button>}
        </div>
      );
    }

    return null;
  }

  // ── Tab style ─────────────────────────────────────────────────────────────
  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 18px", border: "none",
    borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
    background: "none", cursor: "pointer",
    fontWeight: tab === t ? 700 : 400,
    color: tab === t ? "#2563eb" : "#6b7280",
    fontSize: 14, transition: "color 0.15s",
  });

  function handleDrillDown(id: number, name: string) { setDrillAccount({ id, name }); }

  return (
    <>
      {renderFilterBar()}

      <div className="page-header" style={{ paddingTop: showFilterBar ? 56 : undefined }}>
        <h1>CRM Dashboard</h1>
      </div>

      <div className="page-body">
        <div style={{ display: "flex", borderBottom: "1px solid #e5e7eb", marginBottom: 20, gap: 4 }}>
          {(["summary", "companies", "opportunities", "owners"] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => {
              setTab(t);
              if (t !== "companies") setDrillAccount(null);
            }}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {tab === "summary" && <SummaryTab />}

        {tab === "companies" && !drillAccount && (
          <CompaniesTab
            onDrillDown={handleDrillDown}
            search={cmpSearch}
            viewFilter={cmpView}
            sortCol={cmpSortCol}
            sortDir={cmpSortDir}
            onSort={handleCmpSort}
          />
        )}

        {tab === "companies" && drillAccount && (
          <CompanyDetail
            id={drillAccount.id}
            name={drillAccount.name}
            onBack={() => setDrillAccount(null)}
          />
        )}

        {tab === "opportunities" && (
          <OpportunitiesTab
            stageFilter={oppStage}
            ownerFilter={oppOwner}
            periodFilter={oppPeriod}
            accountSearch={oppAccount}
            activeOnly={oppActiveOnly}
            page={oppPage}
            setPage={setOppPage}
          />
        )}

        {tab === "owners" && <OwnersTab myTeamOnly={ownMyTeam} />}
      </div>
    </>
  );
}
