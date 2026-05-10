import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { fetchCompanies, fetchFilterOptions, fetchStatusSummary, lookupCompany, addCompany } from "../api/client";
import type {
  Company, FilterOptions, StatusSummary, ValueChainPosition, CompanyStatus,
  CompanyLookupResult, CompanyAddRequest,
} from "../types";
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

const SUPPLY_CHAIN_OPTIONS = ["Upstream", "Midstream", "Downstream", "Integrated", "Petrochemicals", "Services"];
const VALUE_CHAIN_OPTIONS: ValueChainPosition[] = ["Upstream", "Midstream", "Downstream", "Integrated", "Services"];

function LowConfidenceField({ low, children }: { low: boolean; children: React.ReactNode }) {
  if (!low) return <>{children}</>;
  return (
    <div style={{ position: "relative" }}>
      <div style={{
        position: "absolute", top: 2, right: 6, fontSize: 10, color: "#92400e",
        background: "#fef3c7", borderRadius: 3, padding: "1px 4px", zIndex: 1, pointerEvents: "none",
      }}>auto</div>
      <div style={{ border: "1.5px solid #f59e0b", borderRadius: 6 }}>{children}</div>
    </div>
  );
}

interface AddCompanyModalProps {
  filterOptions: FilterOptions | null;
  onClose: () => void;
  onAdded: () => void;
}

function AddCompanyModal({ filterOptions, onClose, onAdded }: AddCompanyModalProps) {
  const [isPublic, setIsPublic] = useState(true);
  const [tickerInput, setTickerInput] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupResult, setLookupResult] = useState<CompanyLookupResult | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const [form, setForm] = useState<Partial<CompanyAddRequest>>({
    is_public: true,
    name: "",
    ticker: "",
    exchange: "",
    country: "",
    website: "",
    description: "",
    wwt_territory: "",
    wwt_model: "",
    industry: "",
    value_chain_position: undefined,
    supply_chain_position: "",
  });
  const [confidence, setConfidence] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const tickerRef = useRef<HTMLInputElement>(null);

  useEffect(() => { tickerRef.current?.focus(); }, []);

  function applyLookup(r: CompanyLookupResult) {
    setLookupResult(r);
    setConfidence({
      supply_chain_position: r.supply_chain_confidence,
      wwt_territory: r.wwt_territory_confidence,
    });
    setForm(prev => ({
      ...prev,
      name: r.name || prev.name,
      ticker: r.ticker || prev.ticker,
      exchange: r.exchange || prev.exchange || "",
      country: r.country || prev.country || "",
      website: r.website || prev.website || "",
      description: r.description || prev.description || "",
      industry: r.industry || prev.industry || "",
      supply_chain_position: r.supply_chain_position || prev.supply_chain_position || "",
      wwt_territory: r.wwt_territory || prev.wwt_territory || "",
    }));
  }

  async function handleLookup() {
    if (!tickerInput.trim()) return;
    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);
    try {
      const r = await lookupCompany(tickerInput);
      if (r.error) {
        setLookupError(r.error);
      } else if (r.already_exists) {
        setLookupError(`Already in database (id=${r.existing_id}): ${r.name}`);
      } else {
        applyLookup(r);
      }
    } catch (e: unknown) {
      setLookupError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setLookupLoading(false);
    }
  }

  function field(key: keyof CompanyAddRequest) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(prev => ({ ...prev, [key]: e.target.value || undefined }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name?.trim()) { setSubmitError("Name is required"); return; }
    if (isPublic && !form.ticker?.trim()) { setSubmitError("Ticker is required for public companies"); return; }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await addCompany({
        ...(form as CompanyAddRequest),
        name: form.name!.trim(),
        ticker: isPublic ? form.ticker?.trim() : undefined,
        is_public: isPublic,
      });
      onAdded();
    } catch (e: unknown) {
      setSubmitError(e instanceof Error ? e.message : "Failed to add company");
      setSubmitting(false);
    }
  }

  const inputStyle: React.CSSProperties = { width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13, boxSizing: "border-box" };
  const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 3 };
  const rowStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 };

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 1000,
      display: "flex", alignItems: "center", justifyContent: "center",
    }} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{
        background: "#fff", borderRadius: 12, width: "min(560px, 96vw)",
        maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.25)",
      }}>
        <div style={{ padding: "18px 24px", borderBottom: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Add Company</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6b7280", lineHeight: 1 }}>×</button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Public / Private toggle */}
          <div style={{ display: "flex", gap: 8 }}>
            {[true, false].map(pub => (
              <button key={String(pub)} type="button" onClick={() => setIsPublic(pub)}
                style={{
                  flex: 1, padding: "8px 0", borderRadius: 6, border: "1.5px solid",
                  borderColor: isPublic === pub ? "#2563eb" : "#d1d5db",
                  background: isPublic === pub ? "#eff6ff" : "#fff",
                  color: isPublic === pub ? "#1d4ed8" : "#374151",
                  fontWeight: isPublic === pub ? 700 : 400, fontSize: 13, cursor: "pointer",
                }}>
                {pub ? "Public (listed)" : "Private (unlisted)"}
              </button>
            ))}
          </div>

          {/* Ticker + Lookup */}
          {isPublic && (
            <div>
              <label style={labelStyle}>Ticker *</label>
              <div style={{ display: "flex", gap: 8 }}>
                <input ref={tickerRef} style={{ ...inputStyle, flex: 1, textTransform: "uppercase", fontFamily: "monospace" }}
                  value={tickerInput}
                  onChange={e => { setTickerInput(e.target.value.toUpperCase()); setLookupResult(null); setLookupError(null); }}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleLookup(); } }}
                  placeholder="e.g. XOM or BRPT.JK"
                />
                <button type="button" onClick={handleLookup} disabled={lookupLoading || !tickerInput.trim()}
                  style={{
                    padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer",
                    background: "#2563eb", color: "#fff", fontSize: 13, fontWeight: 600,
                    opacity: lookupLoading || !tickerInput.trim() ? 0.6 : 1, whiteSpace: "nowrap",
                  }}>
                  {lookupLoading ? "Looking up…" : "Auto-fill"}
                </button>
              </div>
              {lookupError && <p style={{ margin: "4px 0 0", fontSize: 12, color: "#dc2626" }}>{lookupError}</p>}
              {lookupResult && !lookupResult.error && (
                <p style={{ margin: "4px 0 0", fontSize: 12, color: "#16a34a" }}>
                  Found: <strong>{lookupResult.name}</strong>
                  {lookupResult.market_cap_usd ? ` — ${formatCap(lookupResult.market_cap_usd)}` : ""}
                </p>
              )}
            </div>
          )}

          {/* Name */}
          <div>
            <label style={labelStyle}>Company Name *</label>
            <input style={inputStyle} value={form.name || ""} onChange={field("name")} placeholder="Company name" required />
          </div>

          <div style={rowStyle}>
            {/* Country */}
            <div>
              <label style={labelStyle}>Country</label>
              <input style={inputStyle} value={form.country || ""} onChange={field("country")} placeholder="e.g. United States" />
            </div>
            {/* Exchange */}
            <div>
              <label style={labelStyle}>Exchange</label>
              <input style={inputStyle} value={form.exchange || ""} onChange={field("exchange")} placeholder="e.g. NYSE" />
            </div>
          </div>

          {/* Website */}
          <div>
            <label style={labelStyle}>Website</label>
            <input style={inputStyle} value={form.website || ""} onChange={field("website")} placeholder="https://…" />
          </div>

          {/* Description */}
          <div>
            <label style={labelStyle}>Description</label>
            <textarea style={{ ...inputStyle, resize: "vertical", minHeight: 60 }}
              value={form.description || ""} onChange={field("description")} placeholder="Brief company description…" />
          </div>

          <div style={rowStyle}>
            {/* WWT Territory */}
            <div>
              <label style={labelStyle}>WWT Territory</label>
              <LowConfidenceField low={confidence.wwt_territory === "low" && !!form.wwt_territory}>
                <select style={inputStyle} value={form.wwt_territory || ""} onChange={field("wwt_territory")}>
                  <option value="">— Select —</option>
                  {filterOptions?.wwt_territories.map(t => <option key={t}>{t}</option>)}
                </select>
              </LowConfidenceField>
            </div>
            {/* WWT Model */}
            <div>
              <label style={labelStyle}>WWT Model</label>
              <select style={inputStyle} value={form.wwt_model || ""} onChange={field("wwt_model")}>
                <option value="">— Select —</option>
                {["Chemicals", "Services", "EPC", "Refining", "LNG", "Retail"].map(m => <option key={m}>{m}</option>)}
              </select>
            </div>
          </div>

          <div style={rowStyle}>
            {/* Supply Chain Position */}
            <div>
              <label style={labelStyle}>Energy Value Chain Position</label>
              <LowConfidenceField low={confidence.supply_chain_position === "low" && !!form.supply_chain_position}>
                <select style={inputStyle} value={form.supply_chain_position || ""} onChange={field("supply_chain_position")}>
                  <option value="">— Select —</option>
                  {SUPPLY_CHAIN_OPTIONS.map(p => <option key={p}>{p}</option>)}
                </select>
              </LowConfidenceField>
            </div>
            {/* Value Chain Position */}
            <div>
              <label style={labelStyle}>Value Chain Position</label>
              <select style={inputStyle} value={form.value_chain_position || ""} onChange={field("value_chain_position")}>
                <option value="">— Select —</option>
                {VALUE_CHAIN_OPTIONS.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>

          {/* Energy Industry */}
          <div>
            <label style={labelStyle}>Energy Industry</label>
            <input style={inputStyle} value={form.industry || ""} onChange={field("industry")} placeholder="e.g. Oil & Gas E&P (auto-filled from yfinance)" />
          </div>

          {submitError && <p style={{ margin: 0, fontSize: 13, color: "#dc2626", background: "#fef2f2", padding: "8px 12px", borderRadius: 6 }}>{submitError}</p>}

          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
            <button type="button" onClick={onClose}
              style={{ padding: "8px 18px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 13 }}>
              Cancel
            </button>
            <button type="submit" disabled={submitting}
              style={{ padding: "8px 20px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", opacity: submitting ? 0.7 : 1 }}>
              {submitting ? "Adding…" : "Add Company"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CompanyList() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [statusSummary, setStatusSummary] = useState<StatusSummary | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const tableRef = useRef<HTMLDivElement>(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [territory, setTerritory] = useState("");
  const [industry, setIndustry] = useState("");
  const [supplyChain, setSupplyChain] = useState("");
  const [country, setCountry] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Sort state
  const [sortBy, setSortBy] = useState("market_cap");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    fetchFilterOptions().then(setFilters).catch(() => null);
    fetchStatusSummary().then(setStatusSummary).catch(() => null);
  }, []);

  function handleSort(col: string) {
    if (col === sortBy) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortBy(col);
      // numeric cols default desc, text cols default asc
      setSortDir(["price", "market_cap", "q_rev", "fy_rev"].includes(col) ? "desc" : "asc");
    }
    setPage(1);
  }

  function SortTh({ col, children, right }: { col: string; children: React.ReactNode; right?: boolean }) {
    const active = sortBy === col;
    return (
      <th
        onClick={() => handleSort(col)}
        style={{
          cursor: "pointer", userSelect: "none", whiteSpace: "nowrap",
          textAlign: right ? "right" : "left",
          color: active ? "#2563eb" : undefined,
        }}
      >
        <span style={{ fontWeight: active ? 700 : undefined }}>{children}</span>
        <span style={{ marginLeft: 5, fontSize: 11, color: active ? "#2563eb" : "#9ca3af" }}>
          {active ? (sortDir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </th>
    );
  }

  const selectStyle: React.CSSProperties = {
    padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
    fontSize: 13, background: "#fff", color: "#1a1a2e", cursor: "pointer",
  };

  const anyFilterActive = !!(search || territory || industry || supplyChain || country || statusFilter);

  function handleReset() {
    setSearch(""); setTerritory(""); setIndustry("");
    setSupplyChain(""); setCountry(""); setStatusFilter("");
    setPage(1);
  }

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchCompanies({
      search: search || undefined,
      wwt_territory: territory || undefined,
      industry: industry || undefined,
      supply_chain_position: supplyChain || undefined,
      country: country || undefined,
      status: statusFilter || undefined,
      sort_by: sortBy,
      sort_dir: sortDir,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setCompanies(data.items);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search, territory, industry, supplyChain, country, statusFilter, sortBy, sortDir, page]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleFilterChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  function handleAdded() {
    setShowAddModal(false);
    setToast("Company added successfully");
    setTimeout(() => setToast(null), 4000);
    load();
  }

  return (
    <>
      {toast && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, background: "#16a34a", color: "#fff",
          padding: "12px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
          boxShadow: "0 4px 16px rgba(0,0,0,0.2)", zIndex: 2000,
        }}>
          {toast}
        </div>
      )}
      {showAddModal && (
        <AddCompanyModal
          filterOptions={filters}
          onClose={() => setShowAddModal(false)}
          onAdded={handleAdded}
        />
      )}
      {/* Fixed filter bar — matches Analytics exactly */}
      <div style={{
        position: "fixed", top: 0, left: 220, right: 0, zIndex: 200,
        background: "#1a1a2e", borderBottom: "1px solid rgba(255,255,255,0.1)",
        padding: "10px 28px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
      }}>
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginRight: 8, whiteSpace: "nowrap" }}>Filters</span>
        <input
          type="search" placeholder="Search company name…" value={search}
          onChange={handleFilterChange(setSearch)}
          style={{ ...selectStyle, minWidth: 200 }}
        />
        <select style={selectStyle} value={territory} onChange={handleFilterChange(setTerritory)}>
          <option value="">All WWT Territories</option>
          {filters?.wwt_territories.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select style={selectStyle} value={industry} onChange={handleFilterChange(setIndustry)}>
          <option value="">All Energy Industries</option>
          {filters?.industries.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select style={selectStyle} value={supplyChain} onChange={handleFilterChange(setSupplyChain)}>
          <option value="">All Energy Value Chain Positions</option>
          {filters?.supply_chain_positions.map((v) => <option key={v}>{v}</option>)}
        </select>
        <select style={selectStyle} value={country} onChange={handleFilterChange(setCountry)}>
          <option value="">All Countries</option>
          {filters?.countries.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select style={selectStyle} value={statusFilter} onChange={handleFilterChange(setStatusFilter)}>
          <option value="">Active Only</option>
          <option value="all">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Acquired">Acquired</option>
          <option value="Merged">Merged</option>
          <option value="Delisted">Delisted</option>
          <option value="Unknown">Unknown</option>
          <option value="Sanctioned">Sanctioned</option>
          <option value="Non-Equity">Non-Equity</option>
        </select>
        {anyFilterActive && (
          <button onClick={handleReset} style={{
            padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
            fontSize: 13, background: "#fff", color: "#6b7280", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap",
          }}>
            ↺ Reset
          </button>
        )}
      </div>

      <div className="page-header" style={{ paddingTop: 56 }}>
        <h1>Companies</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: "#6b7280", fontSize: 13 }}>{total.toLocaleString()} companies</span>
          <button
            onClick={() => setShowAddModal(true)}
            style={{
              padding: "7px 16px", borderRadius: 6, border: "none", background: "#2563eb",
              color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer",
            }}>
            + Add Company
          </button>
        </div>
      </div>
      <div className="page-body">
        <SupplyChainChart
          selectedPosition={supplyChain}
          onSelect={(pos) => {
            const next = pos && pos !== supplyChain ? pos : "";
            setSupplyChain(next);
            setPage(1);
            if (next) setTimeout(() => tableRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
          }}
        />

        {statusSummary && <StatusSummaryBar summary={statusSummary} />}

        {error && <div className="error">{error}</div>}

        <div className="card" style={{ padding: 0 }} ref={tableRef}>
          <div className="table-wrap">
            {loading ? (
              <div className="loading">Loading...</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <SortTh col="name">Company</SortTh>
                    <SortTh col="ticker">Ticker</SortTh>
                    <SortTh col="price" right>Price</SortTh>
                    <SortTh col="country">Country</SortTh>
                    <SortTh col="territory">WWT Territory</SortTh>
                    <SortTh col="supply_chain">Energy Value Chain</SortTh>
                    <SortTh col="segment">Energy Industry</SortTh>
                    <SortTh col="q_rev" right>Q Rev</SortTh>
                    <SortTh col="fy_rev" right>FY Rev</SortTh>
                    <SortTh col="market_cap" right>Market Cap</SortTh>
                  </tr>
                </thead>
                <tbody>
                  {companies.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ textAlign: "center", padding: "32px", color: "#9ca3af" }}>
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
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatPrice(c.latest_price)}</td>
                        <td>{c.country ?? "—"}</td>
                        <td>{c.wwt_territory ? <span className="badge badge-territory">{c.wwt_territory}</span> : "—"}</td>
                        <td>{c.supply_chain_position ? <span className="badge badge-supply-chain">{c.supply_chain_position}</span> : "—"}</td>
                        <td>{c.industry ? <span className="badge badge-segment">{c.industry}</span> : "—"}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#6b7280" }}>
                          {c.latest_quarterly_revenue ? `${formatCap(c.latest_quarterly_revenue)}${c.latest_quarter_label ? ` ${c.latest_quarter_label}` : ""}` : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#6b7280" }}>
                          {c.latest_revenue ? `${formatCap(c.latest_revenue)}${c.latest_fiscal_year_label ? ` ${c.latest_fiscal_year_label}` : ""}` : "—"}
                        </td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCap(c.latest_market_cap)}</td>
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
