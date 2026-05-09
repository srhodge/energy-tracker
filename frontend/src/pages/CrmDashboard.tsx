import { useEffect, useState, useMemo } from "react";
import {
  fetchCrmSummary, fetchCrmCompanies, fetchCrmCompany,
  fetchCrmOpportunities, fetchCrmOwners,
} from "../api/client";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "—";
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

function stageBadgeStyle(stage: string | null): React.CSSProperties {
  const s = (stage || "").toLowerCase();
  if (s === "closed won")    return { background: "#dcfce7", color: "#15803d" };
  if (s.includes("closed"))  return { background: "#fee2e2", color: "#dc2626" };
  return { background: "#eff6ff", color: "#2563eb" };
}

const PAGE_SIZE = 50;

type Tab = "summary" | "companies" | "opportunities" | "owners";

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

// ── Summary tab ───────────────────────────────────────────────────────────────

function SummaryTab() {
  const [data, setData]     = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCrmSummary().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading…</div>;
  if (!data)   return <div className="error">Failed to load summary.</div>;

  return (
    <>
      <div className="stat-grid">
        <StatCard label="Open Pipeline"    value={fmt(data.open_pipeline)} />
        <StatCard label="Closed Won"       value={fmt(data.closed_won)} />
        <StatCard label="Win Rate"         value={pct(data.win_rate)} sub="closed won ÷ decided" />
        <StatCard label="Avg Deal Size"    value={fmt(data.avg_deal_size)} sub="closed won deals" />
        <StatCard label="Total Deals"      value={data.total_opportunities.toLocaleString()} />
        <StatCard label="Accounts"         value={data.total_accounts.toLocaleString()} />
      </div>

      <div className="card">
        <h3 style={{ margin: "0 0 12px", fontSize: 14, fontWeight: 600, color: "#374151" }}>
          Pipeline by Stage
        </h3>
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
                  <span style={{
                    display: "inline-block", padding: "2px 8px", borderRadius: 4,
                    fontSize: 12, fontWeight: 500,
                    ...stageBadgeStyle(s.stage),
                  }}>
                    {s.stage}
                  </span>
                </td>
                <td style={{ textAlign: "right" }}>{s.count.toLocaleString()}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {fmt(s.total_amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

// ── Companies tab ─────────────────────────────────────────────────────────────

function CompaniesTab({ onDrillDown }: { onDrillDown: (id: number, name: string) => void }) {
  const [rows, setRows]       = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCrmCompanies()
      .then(data => setRows([...data].sort((a, b) => (b.open_pipeline ?? 0) - (a.open_pipeline ?? 0))))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading…</div>;

  return (
    <div className="card" style={{ padding: 0 }}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Account</th>
              <th style={{ textAlign: "right" }}>Total Deals</th>
              <th style={{ textAlign: "right" }}>Open Pipeline</th>
              <th style={{ textAlign: "right" }}>Closed Won</th>
              <th style={{ textAlign: "right" }}>Closed Lost</th>
              <th style={{ textAlign: "right" }}>Win Rate</th>
              <th style={{ textAlign: "right" }}>Latest Close</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => (
              <tr key={r.id}>
                <td>
                  <button
                    onClick={() => onDrillDown(r.id, r.name)}
                    style={{
                      background: "none", border: "none", cursor: "pointer",
                      fontWeight: 600, color: "#2563eb", fontSize: 14, padding: 0,
                      textDecoration: "underline",
                      textDecorationColor: "rgba(37,99,235,0.4)",
                    }}
                  >
                    {r.name}
                  </button>
                </td>
                <td style={{ textAlign: "right" }}>{r.total_deals}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(r.open_pipeline)}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#15803d" }}>{fmt(r.closed_won)}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#dc2626" }}>{fmt(r.closed_lost)}</td>
                <td style={{ textAlign: "right" }}>{pct(r.win_rate)}</td>
                <td style={{ textAlign: "right", color: "#6b7280", fontSize: 13 }}>{r.latest_close_date ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Company detail (drill-down) ───────────────────────────────────────────────

function CompanyDetail({ id, name, onBack }: { id: number; name: string; onBack: () => void }) {
  const [data, setData]       = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [stageFilter, setStageFilter] = useState("");

  useEffect(() => {
    fetchCrmCompany(id).then(setData).finally(() => setLoading(false));
  }, [id]);

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
        <select
          value={stageFilter}
          onChange={e => setStageFilter(e.target.value)}
          style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13 }}
        >
          <option value="">All Stages</option>
          {stages.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Opportunity</th>
                <th>Owner</th>
                <th>Stage</th>
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
                  <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {o.opportunity_name}
                  </td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.opportunity_owner ?? "—"}</td>
                  <td>
                    <span style={{
                      display: "inline-block", padding: "2px 7px", borderRadius: 4,
                      fontSize: 11, fontWeight: 500, ...stageBadgeStyle(o.stage),
                    }}>
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

function OpportunitiesTab() {
  const [data, setData]             = useState<any>(null);
  const [loading, setLoading]       = useState(true);
  const [stageFilter, setStageFilter]   = useState("");
  const [ownerFilter, setOwnerFilter]   = useState("");
  const [periodFilter, setPeriodFilter] = useState("");
  const [page, setPage]               = useState(1);

  useEffect(() => {
    setLoading(true);
    fetchCrmOpportunities({
      stage:         stageFilter  || undefined,
      owner:         ownerFilter  || undefined,
      fiscal_period: periodFilter || undefined,
      page,
      page_size: PAGE_SIZE,
    }).then(setData).finally(() => setLoading(false));
  }, [stageFilter, ownerFilter, periodFilter, page]);

  const resetPage = () => setPage(1);

  const pageCount = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  const selectStyle: React.CSSProperties = {
    padding: "6px 10px", borderRadius: 6,
    border: "1px solid #d1d5db", fontSize: 13,
  };

  return (
    <>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input
          placeholder="Filter by stage…"
          value={stageFilter}
          onChange={e => { setStageFilter(e.target.value); resetPage(); }}
          style={{ ...selectStyle, width: 180 }}
        />
        <input
          placeholder="Filter by owner…"
          value={ownerFilter}
          onChange={e => { setOwnerFilter(e.target.value); resetPage(); }}
          style={{ ...selectStyle, width: 200 }}
        />
        <input
          placeholder="Fiscal period (e.g. Q3-2024)…"
          value={periodFilter}
          onChange={e => { setPeriodFilter(e.target.value); resetPage(); }}
          style={{ ...selectStyle, width: 220 }}
        />
        {(stageFilter || ownerFilter || periodFilter) && (
          <button
            onClick={() => { setStageFilter(""); setOwnerFilter(""); setPeriodFilter(""); resetPage(); }}
            style={{ ...selectStyle, background: "#f3f4f6", cursor: "pointer", border: "1px solid #d1d5db" }}
          >
            Clear
          </button>
        )}
      </div>

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
                <th>Opportunity</th>
                <th>Account</th>
                <th>Owner</th>
                <th>Stage</th>
                <th>Fiscal Period</th>
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
                  <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {o.opportunity_name}
                  </td>
                  <td style={{ color: "#374151", fontSize: 13 }}>{o.account_name ?? "—"}</td>
                  <td style={{ color: "#6b7280", fontSize: 13 }}>{o.opportunity_owner ?? "—"}</td>
                  <td>
                    <span style={{
                      display: "inline-block", padding: "2px 7px", borderRadius: 4,
                      fontSize: 11, fontWeight: 500, ...stageBadgeStyle(o.stage),
                    }}>
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

function OwnersTab() {
  const [rows, setRows]       = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCrmOwners().then(setRows).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading…</div>;

  return (
    <div className="card" style={{ padding: 0 }}>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Owner</th>
              <th style={{ textAlign: "right" }}>Total Deals</th>
              <th style={{ textAlign: "right" }}>Open Pipeline</th>
              <th style={{ textAlign: "right" }}>Closed Won</th>
              <th style={{ textAlign: "right" }}>Closed Lost</th>
              <th style={{ textAlign: "right" }}>Win Rate</th>
              <th style={{ textAlign: "right" }}>Avg Deal Size</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any, i: number) => (
              <tr key={r.opportunity_owner}>
                <td style={{ color: "#9ca3af", fontVariantNumeric: "tabular-nums", width: 32 }}>{i + 1}</td>
                <td style={{ fontWeight: 600 }}>{r.opportunity_owner}</td>
                <td style={{ textAlign: "right" }}>{r.total_deals.toLocaleString()}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{fmt(r.open_pipeline)}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#15803d" }}>{fmt(r.closed_won)}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#dc2626" }}>{fmt(r.closed_lost)}</td>
                <td style={{ textAlign: "right" }}>{pct(r.win_rate)}</td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#6b7280" }}>{fmt(r.avg_deal_size)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function CrmDashboard() {
  const [tab, setTab]                     = useState<Tab>("summary");
  const [drillAccount, setDrillAccount]   = useState<{ id: number; name: string } | null>(null);

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 18px",
    border: "none",
    borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
    background: "none",
    cursor: "pointer",
    fontWeight: tab === t ? 700 : 400,
    color: tab === t ? "#2563eb" : "#6b7280",
    fontSize: 14,
    transition: "color 0.15s",
  });

  function handleDrillDown(id: number, name: string) {
    setDrillAccount({ id, name });
    setTab("companies");
  }

  return (
    <>
      <div className="page-header">
        <h1>CRM Dashboard</h1>
      </div>
      <div className="page-body">
        {/* Tab bar */}
        <div style={{
          display: "flex", borderBottom: "1px solid #e5e7eb",
          marginBottom: 20, gap: 4,
        }}>
          {(["summary", "companies", "opportunities", "owners"] as Tab[]).map(t => (
            <button key={t} style={tabStyle(t)} onClick={() => { setTab(t); if (t !== "companies") setDrillAccount(null); }}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {tab === "summary"       && <SummaryTab />}
        {tab === "companies"     && !drillAccount && (
          <CompaniesTab onDrillDown={handleDrillDown} />
        )}
        {tab === "companies"     && drillAccount && (
          <CompanyDetail
            id={drillAccount.id}
            name={drillAccount.name}
            onBack={() => setDrillAccount(null)}
          />
        )}
        {tab === "opportunities" && <OpportunitiesTab />}
        {tab === "owners"        && <OwnersTab />}
      </div>
    </>
  );
}
