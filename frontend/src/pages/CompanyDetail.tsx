import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCompany, fetchCompanyByTicker, updateCompany, deleteCompany, setRevenue, fetchCompanyIntelligence, calculateSpendEstimate, fetchCompanyLeadership } from "../api/client";
import type { CompanyDetail as CompanyDetailType, CompanyUpdateRequest, ValueChainPosition, CompanyStatus, IntelligenceData, LeadershipRecord } from "../types";
import { formatCap, formatPrice } from "../components/FormatCap";

const SUPPLY_CHAIN_OPTIONS = ["Upstream", "Midstream", "Downstream", "Integrated", "Petrochemicals", "Services"];
const VALUE_CHAIN_OPTIONS: ValueChainPosition[] = ["Upstream", "Midstream", "Downstream", "Integrated", "Services"];
const STATUS_OPTIONS: CompanyStatus[] = ["Active", "Acquired", "Merged", "Delisted", "Unknown", "Sanctioned", "Non-Equity"];
const WWT_MODELS = ["Chemicals", "Services", "EPC", "Refining", "LNG", "Retail"];

interface EditModalProps {
  company: CompanyDetailType;
  onClose: () => void;
  onSaved: () => void;
}

function EditCompanyModal({ company, onClose, onSaved }: EditModalProps) {
  const [form, setForm] = useState<CompanyUpdateRequest>({
    name: company.name,
    ticker: company.ticker ?? "",
    exchange: company.exchange ?? "",
    country: company.country ?? "",
    website: company.website ?? "",
    description: company.description ?? "",
    wwt_territory: company.wwt_territory ?? "",
    wwt_model: company.wwt_model ?? "",
    industry: company.industry ?? "",
    value_chain_position: company.value_chain_position,
    supply_chain_position: company.supply_chain_position ?? "",
    status: company.status,
    acquired_by: company.acquired_by ?? "",
    acquisition_notes: company.acquisition_notes ?? "",
    ce_name: company.ce_name ?? "",
    ce_email: company.ce_email ?? "",
    ce_phone: company.ce_phone ?? "",
  });
  const [revLocked, setRevLocked] = useState(company.revenue_manually_set ?? false);
  const [revAmount, setRevAmount] = useState(
    company.latest_revenue ? String(Math.round(company.latest_revenue)) : ""
  );
  const [revFY, setRevFY] = useState(company.latest_fiscal_year_label ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function field(key: keyof CompanyUpdateRequest) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm(prev => ({ ...prev, [key]: e.target.value || undefined }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name?.trim()) { setError("Name is required"); return; }
    setSaving(true);
    setError(null);
    try {
      const payload: CompanyUpdateRequest = {};
      for (const [k, v] of Object.entries(form)) {
        (payload as Record<string, unknown>)[k] = typeof v === "string" ? (v.trim() || undefined) : v;
      }
      payload.name = form.name!.trim();

      // Handle revenue lock state change
      const revAmountNum = revAmount.trim() ? parseFloat(revAmount.replace(/,/g, "")) : null;
      const revChanged = revAmountNum !== null && (
        revAmountNum !== company.latest_revenue || revFY.trim() !== (company.latest_fiscal_year_label ?? "")
      );
      if (revLocked && revChanged && revAmountNum && revFY.trim()) {
        await setRevenue(company.id, revAmountNum, revFY.trim());
        // set-revenue already sets revenue_manually_set=true on the backend
      } else if (revLocked !== (company.revenue_manually_set ?? false) && !revChanged) {
        payload.revenue_manually_set = revLocked;
      }

      await updateCompany(company.id, payload);
      onSaved();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = { width: "100%", padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13, boxSizing: "border-box" };
  const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 3 };
  const rowStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: "#fff", borderRadius: 12, width: "min(580px, 96vw)", maxHeight: "90vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.25)" }}>
        <div style={{ padding: "18px 24px", borderBottom: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Edit Company</h2>
          <button onClick={onClose} style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#6b7280", lineHeight: 1 }}>×</button>
        </div>
        <form onSubmit={handleSubmit} style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Company Name *</label>
              <input style={inputStyle} value={form.name ?? ""} onChange={field("name")} required />
            </div>
            <div>
              <label style={labelStyle}>Ticker</label>
              <input style={{ ...inputStyle, fontFamily: "monospace", textTransform: "uppercase" }} value={form.ticker ?? ""} onChange={field("ticker")} placeholder="e.g. XOM" />
            </div>
          </div>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Country</label>
              <input style={inputStyle} value={form.country ?? ""} onChange={field("country")} />
            </div>
            <div>
              <label style={labelStyle}>Exchange</label>
              <input style={inputStyle} value={form.exchange ?? ""} onChange={field("exchange")} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Website</label>
            <input style={inputStyle} value={form.website ?? ""} onChange={field("website")} placeholder="https://…" />
          </div>
          <div>
            <label style={labelStyle}>Description</label>
            <textarea style={{ ...inputStyle, resize: "vertical", minHeight: 60 }} value={form.description ?? ""} onChange={field("description")} />
          </div>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>WWT Territory</label>
              <input style={inputStyle} value={form.wwt_territory ?? ""} onChange={field("wwt_territory")} placeholder="e.g. Americas" />
            </div>
            <div>
              <label style={labelStyle}>WWT Model</label>
              <select style={inputStyle} value={form.wwt_model ?? ""} onChange={field("wwt_model")}>
                <option value="">— Select —</option>
                {WWT_MODELS.map(m => <option key={m}>{m}</option>)}
              </select>
            </div>
          </div>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Energy Value Chain Position</label>
              <select style={inputStyle} value={form.supply_chain_position ?? ""} onChange={field("supply_chain_position")}>
                <option value="">— Select —</option>
                {SUPPLY_CHAIN_OPTIONS.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Value Chain Position</label>
              <select style={inputStyle} value={form.value_chain_position ?? ""} onChange={field("value_chain_position")}>
                <option value="">— Select —</option>
                {VALUE_CHAIN_OPTIONS.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label style={labelStyle}>Energy Industry</label>
            <input style={inputStyle} value={form.industry ?? ""} onChange={field("industry")} placeholder="e.g. Oil & Gas E&P" />
          </div>
          <div style={rowStyle}>
            <div>
              <label style={labelStyle}>Status</label>
              <select style={inputStyle} value={form.status ?? ""} onChange={field("status")}>
                {STATUS_OPTIONS.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Acquired By</label>
              <input style={inputStyle} value={form.acquired_by ?? ""} onChange={field("acquired_by")} placeholder="Acquiring company name" />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Notes</label>
            <input style={inputStyle} value={form.acquisition_notes ?? ""} onChange={field("acquisition_notes")} placeholder="e.g. Acquired Q2 2024" />
          </div>
          <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", marginBottom: 8 }}>
              CLIENT EXECUTIVE <span style={{ fontWeight: 400, color: "#9ca3af", fontSize: 11 }}>Admin only</span>
            </div>
            <div style={rowStyle}>
              <div>
                <label style={labelStyle}>Name</label>
                <input style={inputStyle} value={form.ce_name ?? ""} onChange={field("ce_name")} placeholder="e.g. Jane Smith" />
              </div>
              <div>
                <label style={labelStyle}>Phone</label>
                <input style={inputStyle} value={form.ce_phone ?? ""} onChange={field("ce_phone")} placeholder="e.g. +1 314 555 0100" />
              </div>
            </div>
            <div style={{ marginTop: 10 }}>
              <label style={labelStyle}>Email</label>
              <input style={inputStyle} value={form.ce_email ?? ""} onChange={field("ce_email")} placeholder="e.g. jane.smith@wwt.com" type="email" />
            </div>
          </div>
          <div style={{ borderTop: "1px solid #e5e7eb", paddingTop: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              REVENUE OVERRIDE
              {revLocked && <span style={{ fontSize: 11, color: "#16a34a", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 4, padding: "1px 6px" }}>locked</span>}
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={revLocked} onChange={e => setRevLocked(e.target.checked)} />
              Lock revenue (prevent auto-update from poller)
            </label>
            {revLocked && (
              <div style={rowStyle}>
                <div>
                  <label style={labelStyle}>Revenue (USD)</label>
                  <input
                    style={inputStyle}
                    value={revAmount}
                    onChange={e => setRevAmount(e.target.value)}
                    placeholder="e.g. 1500000000"
                    type="number"
                    min="0"
                  />
                </div>
                <div>
                  <label style={labelStyle}>Fiscal Year</label>
                  <input
                    style={inputStyle}
                    value={revFY}
                    onChange={e => setRevFY(e.target.value)}
                    placeholder="e.g. FY2024"
                  />
                </div>
              </div>
            )}
          </div>
          {error && <p style={{ margin: 0, fontSize: 13, color: "#dc2626", background: "#fef2f2", padding: "8px 12px", borderRadius: 6 }}>{error}</p>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", paddingTop: 4 }}>
            <button type="button" onClick={onClose} style={{ padding: "8px 18px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer", fontSize: 13 }}>Cancel</button>
            <button type="submit" disabled={saving} style={{ padding: "8px 20px", borderRadius: 6, border: "none", background: "#2563eb", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", opacity: saving ? 0.7 : 1 }}>
              {saving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Intelligence helpers ──────────────────────────────────────────────────────

const TIER_STYLE: Record<number, { bg: string; border: string; color: string }> = {
  1: { bg: "#fef9c3", border: "#fde047", color: "#854d0e" },
  2: { bg: "#eff6ff", border: "#bfdbfe", color: "#1d4ed8" },
  3: { bg: "#f0fdf4", border: "#bbf7d0", color: "#166534" },
};

function TierBadge({ tier }: { tier?: number }) {
  if (tier == null) return <span style={{ color: "#9ca3af", fontSize: 13 }}>Not collected</span>;
  const s = TIER_STYLE[tier] ?? { bg: "#f3f4f6", border: "#d1d5db", color: "#374151" };
  return (
    <span style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color, borderRadius: 5, padding: "2px 9px", fontSize: 12, fontWeight: 700 }}>
      T{tier}
    </span>
  );
}

function ConfBadge({ level }: { level?: string }) {
  if (!level) return null;
  const s =
    level === "HIGH"        ? { bg: "#f0fdf4", color: "#166534", border: "#bbf7d0" } :
    level === "MEDIUM_HIGH" ? { bg: "#ecfdf5", color: "#065f46", border: "#6ee7b7" } :
    level === "MEDIUM"      ? { bg: "#fffbeb", color: "#92400e", border: "#fde68a" } :
    level === "LOW_MEDIUM"  ? { bg: "#fff7ed", color: "#9a3412", border: "#fed7aa" } :
                              { bg: "#fef2f2", color: "#991b1b", border: "#fecaca" };
  return (
    <span style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}`, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700, letterSpacing: "0.03em" }}>
      {level.replace("_", " ")}
    </span>
  );
}

const SIGNAL_TYPE_COLOR: Record<string, string> = {
  partnership:      "#0ea5e9",
  ai_announcement:  "#7c3aed",
  leadership_hire:  "#16a34a",
  contract_win:     "#2563eb",
  earnings_signal:  "#f59e0b",
  regulatory:       "#6b7280",
};

function SignalTypeBadge({ type }: { type: string }) {
  const color = SIGNAL_TYPE_COLOR[type] ?? "#6b7280";
  return (
    <span style={{ background: color, color: "#fff", borderRadius: 4, padding: "2px 7px", fontSize: 11, fontWeight: 600, whiteSpace: "nowrap" }}>
      {type.replace(/_/g, " ")}
    </span>
  );
}

function DirectionIcon({ dir }: { dir?: string }) {
  if (dir === "up")   return <span style={{ color: "#16a34a", fontWeight: 700, fontSize: 15 }}>↑</span>;
  if (dir === "down") return <span style={{ color: "#dc2626", fontWeight: 700, fontSize: 15 }}>↓</span>;
  return <span style={{ color: "#9ca3af", fontSize: 15 }}>→</span>;
}

function NC() {
  return <span style={{ color: "#9ca3af", fontSize: 13 }}>Not collected</span>;
}

function IntelligenceTab({ companyId, companyName }: { companyId: number; companyName: string }) {
  const [data, setData]           = useState<IntelligenceData | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);
  const [showPast, setShowPast]   = useState(false);
  const [allLeaders, setAllLeaders] = useState<LeadershipRecord[] | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);
  const [showAddrPanel, setShowAddrPanel] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchCompanyIntelligence(companyId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyId]);

  async function handleShowPast() {
    if (!showPast && allLeaders === null) {
      const all = await fetchCompanyLeadership(companyId, false);
      setAllLeaders(all);
    }
    setShowPast(p => !p);
  }

  async function handleCalculate() {
    setCalculating(true);
    setCalcError(null);
    try {
      await calculateSpendEstimate(companyId);
      const fresh = await fetchCompanyIntelligence(companyId);
      setData(fresh);
    } catch (e: unknown) {
      setCalcError(e instanceof Error ? e.message : "Calculation failed");
    } finally {
      setCalculating(false);
    }
  }

  if (loading) return <div className="loading" style={{ padding: "32px 0" }}>Loading intelligence data…</div>;
  if (error)   return <div className="error" style={{ marginTop: 16 }}>{error}</div>;
  if (!data)   return null;

  const { profile: p, signals, leadership, latest_estimate: est, crm_summary: crm } = data;
  const visibleLeaders = showPast ? (allLeaders ?? leadership) : leadership.filter(l => l.is_current);

  const tdL: React.CSSProperties = { padding: "7px 10px", fontSize: 13, color: "#374151", borderBottom: "1px solid #f3f4f6", fontWeight: 500, whiteSpace: "nowrap" };
  const tdV: React.CSSProperties = { padding: "7px 10px", fontSize: 13, color: "#1a1a2e", borderBottom: "1px solid #f3f4f6", textAlign: "right" };
  const tdVB: React.CSSProperties = { ...tdV, fontWeight: 700 };

  function spendRow(label: string, low?: number, mid?: number, high?: number, bold = false, totalLow?: number, totalMid?: number, totalHigh?: number, fy2027e?: number, confidenceLevel?: string) {
    const cell = bold ? tdVB : tdV;
    const rowBg = bold ? "#f8fafc" : undefined;
    const pctLow  = (!bold && totalLow  && low  != null && totalLow  > 0) ? Math.round((low  / totalLow)  * 100) : null;
    const pctMid  = (!bold && totalMid  && mid  != null && totalMid  > 0) ? Math.round((mid  / totalMid)  * 100) : null;
    const pctHigh = (!bold && totalHigh && high != null && totalHigh > 0) ? Math.round((high / totalHigh) * 100) : null;
    const confPill = !bold && confidenceLevel ? (
      <span style={{
        display: "inline-block", marginLeft: 6, padding: "1px 5px", borderRadius: 3, fontSize: 10, fontWeight: 700,
        background: confidenceLevel === "HIGH" ? "#f0fdf4" : confidenceLevel.startsWith("MEDIUM") ? "#fffbeb" : "#f3f4f6",
        color:      confidenceLevel === "HIGH" ? "#166534" : confidenceLevel.startsWith("MEDIUM") ? "#92400e" : "#6b7280",
        border: `1px solid ${confidenceLevel === "HIGH" ? "#bbf7d0" : confidenceLevel.startsWith("MEDIUM") ? "#fde68a" : "#d1d5db"}`,
      }}>
        {confidenceLevel === "HIGH" ? "HIGH" : confidenceLevel.startsWith("MEDIUM") ? "MED" : "LOW"}
      </span>
    ) : null;
    return (
      <tr key={label} style={{ background: rowBg }}>
        <td style={{ ...tdL, fontWeight: bold ? 700 : 500, paddingLeft: bold ? 10 : 14 }}>{label}{confPill}</td>
        <td style={{ ...cell, color: "#6b7280" }}>
          {low != null ? <>{formatCap(low)}{pctLow != null && <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: 4 }}>({pctLow}%)</span>}</> : "—"}
        </td>
        <td style={cell}>
          {mid != null ? <>{formatCap(mid)}{pctMid != null && <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: 4 }}>({pctMid}%)</span>}</> : "—"}
        </td>
        <td style={{ ...cell, color: "#16a34a" }}>
          {high != null ? <>{formatCap(high)}{pctHigh != null && <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: 4 }}>({pctHigh}%)</span>}</> : "—"}
        </td>
        <td style={{ ...cell, color: "#F59E0B" }} title="Forward estimate based on 8% annual growth assumption applied to HIGH scenario">
          {fy2027e != null ? formatCap(fy2027e) : "—"}
        </td>
      </tr>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Row 1: Profile + Estimate ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

        {/* Company Profile */}
        <div className="detail-section card">
          <h2 style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            Company Profile
            <TierBadge tier={p.data_enrichment_tier} />
          </h2>
          <dl className="detail-kv">
            <dt>Sub-sector</dt>
            <dd>{p.sub_sector ?? <NC />}</dd>

            <dt>Employees</dt>
            <dd>
              {p.employee_count != null
                ? <>
                    {p.employee_count.toLocaleString()}
                    {p.employee_count_source && (
                      <span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>
                        ({p.employee_count_source.replace(/_/g, " ")})
                      </span>
                    )}
                  </>
                : <NC />}
            </dd>

            <dt>HQ Location</dt>
            <dd>{(p.hq_city || p.hq_country) ? [p.hq_city, p.hq_country].filter(Boolean).join(", ") : <NC />}</dd>

            <dt>Tech Decision City</dt>
            <dd>{(p.tech_decision_city || p.tech_decision_country) ? [p.tech_decision_city, p.tech_decision_country].filter(Boolean).join(", ") : <NC />}</dd>

            <dt>Revenue TTM</dt>
            <dd>
              {p.revenue_ttm != null
                ? <>{formatCap(p.revenue_ttm)}<span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>(annual report 2025)</span></>
                : <NC />}
            </dd>

            <dt>EBITDA TTM</dt>
            <dd>
              {p.ebitda_ttm != null
                ? <>{formatCap(p.ebitda_ttm)}<span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>(annual report 2025)</span></>
                : <NC />}
            </dd>

            <dt>Private</dt>
            <dd>{p.is_private == null ? <NC /> : p.is_private ? "Yes" : "No"}</dd>

            <dt>PE-Backed</dt>
            <dd>{p.is_pe_backed == null ? <NC /> : p.is_pe_backed ? "Yes" : "No"}</dd>

            <dt>Offshore CoE</dt>
            <dd>
              {p.offshore_coe_confirmed == null ? <NC /> : p.offshore_coe_confirmed
                ? <>
                    Confirmed
                    <span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>— reduces addressable by 8%</span>
                  </>
                : "No"}
            </dd>

            <dt>Incumbent MSP</dt>
            <dd>
              {p.incumbent_msp
                ? <>
                    {p.incumbent_msp}
                    <span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>(-10% addressable)</span>
                  </>
                : <NC />}
            </dd>

            <dt>Channel Mismatch</dt>
            <dd>
              {p.channel_mismatch_flag
                ? <>
                    Flagged
                    <span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>(-8% addressable)</span>
                    {p.channel_mismatch_note && <span style={{ fontSize: 11, color: "#6b7280", marginLeft: 6 }}>— {p.channel_mismatch_note}</span>}
                  </>
                : p.channel_mismatch_flag === false ? "Clear" : <NC />}
            </dd>
          </dl>
        </div>

        {/* Spend Estimate */}
        <div className="detail-section card">
          <h2 style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            Technology Spend Estimate
            {est && <><ConfBadge level={est.confidence_level} /><span style={{ fontSize: 11, color: "#6b7280", fontWeight: 400 }}>{est.model_version} · {est.estimate_date}</span></>}
          </h2>

          {est ? (
            <>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={{ ...tdL, color: "#6b7280", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>Category</th>
                    <th style={{ ...tdV, color: "#6b7280", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>Low</th>
                    <th style={{ ...tdVB, fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>Mid</th>
                    <th style={{ ...tdV, color: "#6b7280", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>High</th>
                    <th style={{ ...tdV, color: "#F59E0B", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>FY2027E (est.)</th>
                  </tr>
                </thead>
                <tbody>
                  {spendRow("IT",      est.it_spend_low,      est.it_spend_mid,      est.it_spend_high,      false, est.total_spend_low ?? undefined, est.total_spend_mid ?? undefined, est.total_spend_high ?? undefined, undefined, est.confidence_level ?? undefined)}
                  {spendRow("OT",      est.ot_spend_low,      est.ot_spend_mid,      est.ot_spend_high,      false, est.total_spend_low ?? undefined, est.total_spend_mid ?? undefined, est.total_spend_high ?? undefined, undefined, est.confidence_level ?? undefined)}
                  {spendRow("Digital", est.digital_spend_low, est.digital_spend_mid, est.digital_spend_high, false, est.total_spend_low ?? undefined, est.total_spend_mid ?? undefined, est.total_spend_high ?? undefined, undefined, est.confidence_level ?? undefined)}
                  {spendRow("AI",      est.ai_spend_low,      est.ai_spend_mid,      est.ai_spend_high,      false, est.total_spend_low ?? undefined, est.total_spend_mid ?? undefined, est.total_spend_high ?? undefined, undefined, est.confidence_level ?? undefined)}
                  {spendRow("Total",   est.total_spend_low,   est.total_spend_mid,   est.total_spend_high,   true)}
                  <tr style={{ background: "#eff6ff" }}>
                    <td style={{ ...tdL, fontWeight: 700, color: "#1d4ed8" }}>WWT Addressable</td>
                    <td style={{ ...tdV, color: "#6b7280" }}>
                      {est.wwt_addressable_low != null
                        ? <>{formatCap(est.wwt_addressable_low)}{est.wwt_addressable_pct_low != null && <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: 4 }}>({est.wwt_addressable_pct_low.toFixed(0)}%)</span>}</>
                        : "—"}
                    </td>
                    <td style={{ ...tdVB, color: "#1d4ed8" }}>
                      {(() => {
                        const pct = est.wwt_addressable_pct_low;
                        const mid = est.total_spend_mid != null && pct != null ? est.total_spend_mid * pct / 100 : null;
                        return mid != null
                          ? <>{formatCap(mid)}<span style={{ fontSize: 10, color: "#6b7280", marginLeft: 4 }}>({pct!.toFixed(0)}%)</span></>
                          : pct != null ? <>{pct.toFixed(0)}%</> : "—";
                      })()}
                    </td>
                    <td style={{ ...tdV, color: "#16a34a" }}>
                      {est.wwt_addressable_high != null
                        ? <>{formatCap(est.wwt_addressable_high)}{est.wwt_addressable_pct_high != null && <span style={{ fontSize: 10, color: "#9ca3af", marginLeft: 4 }}>({est.wwt_addressable_pct_high.toFixed(0)}%)</span>}</>
                        : "—"}
                    </td>
                    <td style={{ ...tdV, color: "#F59E0B" }} title="Forward estimate based on 8% annual growth assumption applied to HIGH scenario">
                      {est.wwt_addressable_high != null ? formatCap(est.wwt_addressable_high * 1.08) : "—"}
                    </td>
                  </tr>
                </tbody>
              </table>
              {est.step1_value_chain && (
                <div style={{ marginTop: 6 }}>
                  <button
                    onClick={() => setShowAddrPanel(p => !p)}
                    style={{ background: "none", border: "none", color: "#2563eb", fontSize: 12, cursor: "pointer", padding: 0, textDecoration: "underline" }}
                  >
                    {showAddrPanel ? "Hide calculation" : "Show calculation"}
                  </button>
                </div>
              )}
              {showAddrPanel && est.step1_value_chain && (() => {
                const denom = est.step2_denominator_used;
                const denomVal = denom === "blended" && p.revenue_ttm != null && p.ebitda_ttm != null
                  ? p.revenue_ttm * 0.6 + p.ebitda_ttm * 0.4
                  : denom === "ebitda" ? (p.ebitda_ttm ?? null)
                  : denom === "gross_profit" ? (p.gross_profit_ttm ?? null)
                  : (p.revenue_ttm ?? null);
                const denomLabel = denomVal != null ? `${denom} ${formatCap(denomVal)}` : (denom ?? "revenue");

                const kd = est.key_drivers as Record<string, unknown> | undefined;
                const matScore = typeof kd?.maturity_score === "number" ? kd.maturity_score : 0;
                const estFlags = est.flags as Record<string, unknown> | undefined;

                const oemApplied      = !!(estFlags?.oem_direct_hardware) || (p.revenue_ttm != null && p.revenue_ttm >= 10_000_000_000);
                const offshoreApplied = !!p.offshore_coe_confirmed;
                const mspApplied      = !!(p.incumbent_msp);
                const mismatchApplied = !!p.channel_mismatch_flag;
                const msApplied       = !!p.ms_standardized;
                const aiApplied       = matScore >= 15;

                let rawPct = 27;
                if (oemApplied)       rawPct -= 3;
                if (offshoreApplied)  rawPct -= 8;
                if (mspApplied)       rawPct -= 10;
                if (mismatchApplied)  rawPct -= 8;
                if (msApplied)        rawPct += 5;
                if (aiApplied)        rawPct += 5;

                const finalPct = Math.max(12, Math.min(42, rawPct));
                const isClamped = finalPct !== rawPct;
                const isFloor   = isClamped && finalPct > rawPct;
                const isCeil    = isClamped && finalPct < rawPct;
                const wwtMid    = est.total_spend_mid != null ? est.total_spend_mid * finalPct / 100 : null;

                const parts: string[] = ["27%"];
                if (oemApplied)       parts.push("− 3%");
                if (offshoreApplied)  parts.push("− 8%");
                if (mspApplied)       parts.push("− 10%");
                if (mismatchApplied)  parts.push("− 8%");
                if (msApplied)        parts.push("+ 5%");
                if (aiApplied)        parts.push("+ 5%");

                const GRAY  = "#9ca3af";
                const RED   = "#dc2626";
                const GREEN = "#16a34a";
                const BLUE  = "#1d4ed8";
                const AMBER = "#d97706";

                const coeName = (typeof estFlags?.offshore_coe_name === "string" && estFlags.offshore_coe_name)
                  ? estFlags.offshore_coe_name as string
                  : "India-based technology center";

                function fRow(label: React.ReactNode, value: string, applied: boolean, valueColor: string, valueBold = false) {
                  return (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "5px 0", borderBottom: "1px solid #f3f4f6" }}>
                      <div style={{ fontSize: 12, color: applied ? "#374151" : GRAY, flex: 1, paddingRight: 12 }}>{label}</div>
                      <div style={{ fontSize: 12, fontWeight: valueBold ? 700 : 600, color: applied ? valueColor : GRAY, whiteSpace: "nowrap" }}>{value}</div>
                    </div>
                  );
                }

                return (
                  <div style={{ marginTop: 10, fontSize: 12, color: "#6b7280", borderTop: "1px solid #f3f4f6", paddingTop: 8 }}>
                    <span style={{ fontWeight: 600 }}>Model basis:</span> {est.step1_value_chain} · {denomLabel} denominator · {est.step3_regional_multiplier}x regional

                    {/* ── WWT Addressable Share Panel ── */}
                    <div style={{ marginTop: 10, background: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 7, padding: "12px 14px" }}>
                      <div style={{ marginBottom: 8 }}>
                        <div style={{ fontSize: 12, fontWeight: 700, color: "#1a1a2e" }}>WWT Addressable Share — How We Got Here</div>
                        <div style={{ fontSize: 11, color: GRAY, marginTop: 1 }}>All factors shown. Grayed = not applicable to this company.</div>
                      </div>

                      {fRow(
                        "Base addressable (hardware, networking, IT/OT security, cloud, AI infra)",
                        "+27%", true, "#1a1a2e", true
                      )}
                      {fRow(
                        "Hardware OEM-direct (revenue >$10B — large enterprise buys direct)",
                        oemApplied ? "−3%" : "−3% — not applied",
                        oemApplied, RED
                      )}
                      {fRow(
                        <>Offshore CoE — <em>{coeName}</em></>,
                        offshoreApplied ? "−8%" : "−8% — not applicable",
                        offshoreApplied, RED
                      )}
                      {fRow(
                        <>Incumbent MSP — {p.incumbent_msp
                          ? <em>{p.incumbent_msp}</em>
                          : "managed service provider"}</>,
                        mspApplied ? "−10%" : "−10% — none confirmed",
                        mspApplied, RED
                      )}
                      {fRow(
                        <>
                          Channel mismatch (tech decisions outside account owner territory)
                          {mismatchApplied && p.channel_mismatch_note && (
                            <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>{p.channel_mismatch_note}</div>
                          )}
                        </>,
                        mismatchApplied ? "−8%" : "−8% — clear, no mismatch",
                        mismatchApplied, RED
                      )}
                      {fRow(
                        "Microsoft standardized — Softchoice licensing access",
                        msApplied ? "+5%" : "+5% — not confirmed",
                        msApplied, GREEN
                      )}
                      {fRow(
                        <>High AI maturity (score ≥15) — <span style={{ color: GRAY }}>score: {matScore}</span></>,
                        aiApplied ? "+5%" : "+5% — score below threshold",
                        aiApplied, GREEN
                      )}

                      <div style={{ borderTop: "2px solid #e5e7eb", margin: "8px 0" }} />

                      <div style={{ display: "flex", justifyContent: "space-between", padding: "3px 0" }}>
                        <div style={{ fontSize: 12, color: "#374151" }}>Subtotal before floor/ceiling</div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: "#374151" }}>{parts.join(" ")} = {rawPct}%</div>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #f3f4f6" }}>
                        <div style={{ fontSize: 12, color: isClamped ? AMBER : GRAY }}>Floor/ceiling applied (model bounds: 12%–42%)</div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: isClamped ? AMBER : GRAY }}>
                          {isFloor ? `${rawPct}% → clamped to floor 12%` : isCeil ? `${rawPct}% → clamped to ceiling 42%` : "Within bounds — no adjustment"}
                        </div>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", padding: "8px 0 2px" }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 700, color: "#1a1a2e" }}>= Final WWT addressable share</div>
                          {wwtMid != null && (
                            <div style={{ fontSize: 11, color: GRAY, marginTop: 2 }}>
                              Applied to {denomLabel} → {formatCap(wwtMid)} mid addressable
                            </div>
                          )}
                        </div>
                        <div style={{ fontSize: 22, fontWeight: 800, color: BLUE, lineHeight: 1 }}>{finalPct}%</div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </>
          ) : (
            <div style={{ padding: "24px 0", textAlign: "center" }}>
              <p style={{ color: "#6b7280", fontSize: 13, marginBottom: 16 }}>
                No estimate calculated yet for this company.
              </p>
              {calcError && (
                <p style={{ color: "#dc2626", fontSize: 13, marginBottom: 12, background: "#fef2f2", padding: "8px 12px", borderRadius: 6 }}>
                  {calcError}
                </p>
              )}
              <button
                onClick={handleCalculate}
                disabled={calculating}
                style={{ padding: "9px 22px", borderRadius: 7, border: "none", background: "#2563eb", color: "#fff", fontWeight: 700, fontSize: 13, cursor: "pointer", opacity: calculating ? 0.7 : 1 }}
              >
                {calculating ? "Calculating…" : "Calculate Estimate"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Opportunity Scorecard ── */}
      <div className="detail-section card">
        <h2 style={{ marginBottom: 14 }}>Opportunity Scorecard</h2>
        {est ? (() => {
          const kd = est.key_drivers as Record<string, unknown> | undefined;
          const matScore = typeof kd?.maturity_score === "number" ? kd.maturity_score : 0;
          const techMaturity = matScore >= 20 ? 5 : matScore >= 15 ? 4 : matScore >= 10 ? 3 : matScore >= 5 ? 2 : 1;
          const rev = p.revenue_ttm ?? 0;
          const financialCap = rev >= 100_000_000_000 ? 5 : rev >= 20_000_000_000 ? 4 : rev >= 5_000_000_000 ? 3 : rev >= 1_000_000_000 ? 2 : 1;
          const qualifyingSignals = signals.filter(s =>
            ["leadership_hire", "earnings_signal", "strategic_pivot", "partnership", "ai_announcement"].includes(s.signal_type)
          );
          const urgencyCount = qualifyingSignals.length;
          const strategicUrgency = urgencyCount >= 5 ? 5 : urgencyCount >= 3 ? 4 : urgencyCount >= 2 ? 3 : urgencyCount >= 1 ? 2 : 1;
          const accessibility = (!p.channel_mismatch_flag && !p.incumbent_msp) ? 5 :
                                (!p.channel_mismatch_flag && !!p.incumbent_msp) ? 3 :
                                (!!p.channel_mismatch_flag && !p.incumbent_msp) ? 3 : 1;
          const pipe3yr = crm?.linked ? (crm.pipeline_3yr ?? 0) : 0;
          const won3yr  = crm?.linked ? (crm.closed_won_3yr ?? 0) : 0;
          const wwtAddressableMid = est?.wwt_addressable_mid ?? 0;
          const penetrationRatio = wwtAddressableMid > 0 ? pipe3yr / wwtAddressableMid : 0;

          const warmth = !crm?.linked ? 3
            : penetrationRatio > 0.10 ? 5
            : penetrationRatio > 0.03 ? 4
            : penetrationRatio > 0.01 ? 3
            : penetrationRatio > 0.001 ? 2
            : pipe3yr > 0 ? 1
            : 2;

          const fmtUSD = (n: number) =>
            n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B`
            : n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M`
            : n >= 1e3 ? `$${Math.round(n / 1e3)}K`
            : `$${Math.round(n)}`;

          // ── Per-factor explanatory text ─────────────────────────────────────
          const topSignal = [...signals].sort((a, b) => (b.score_points ?? 0) - (a.score_points ?? 0))[0];
          const techExpl = [
            `${matScore} combined signal score from leadership records and technology signals.`,
            matScore >= 15
              ? "Exceeds WWT high AI maturity threshold — +5% addressable bonus applied to this estimate."
              : `Below ≥15 threshold — ${15 - matScore} additional point${15 - matScore !== 1 ? "s" : ""} needed to unlock +5% AI bonus.`,
            topSignal?.signal_title ? `Top signal: ${topSignal.signal_title}.` : "",
          ].filter(Boolean).join(" ");

          const denominatorBasis = est.step2_denominator_used
            ? `${est.step2_denominator_used} denominator applied.`
            : "Revenue denominator applied.";
          const maSignal = signals.find(s =>
            s.signal_type === "strategic_pivot" && /acqui|merger|m&a/i.test(s.signal_title ?? "")
          );
          const finExpl = [
            p.revenue_ttm
              ? `${formatCap(p.revenue_ttm)} TTM revenue — ${p.sub_sector ?? p.revenue_denominator ?? "unknown sub-sector"}.`
              : "Revenue unknown.",
            denominatorBasis,
            maSignal ? "Active M&A signal detected — near-term IT integration demand likely." : "",
          ].filter(Boolean).join(" ");

          const sortedQS = [...qualifyingSignals].sort((a, b) =>
            new Date(b.signal_date ?? "").getTime() - new Date(a.signal_date ?? "").getTime()
          );
          const urgencyExpl = urgencyCount === 0
            ? "0 qualifying signals in the past 730 days. No active forcing functions identified — stable execution phase. Monitor for M&A announcements, CEO transitions, or strategic pivot signals."
            : [
                `${urgencyCount} qualifying signal${urgencyCount !== 1 ? "s" : ""} in the past 730 days.`,
                `Recent signals: ${sortedQS.slice(0, 2).map(s => s.signal_title).join("; ")}.`,
              ].join(" ");

          const accessExpl = [
            p.wwt_territory ? `${p.wwt_territory} territory.` : "Territory unknown.",
            p.channel_mismatch_flag
              ? `Tech decisions in ${p.tech_decision_city ?? "unknown city"} — outside WWT account territory.`
              : "",
            p.incumbent_msp
              ? `Incumbent MSP: ${p.incumbent_msp} — displacement required for managed services engagement.`
              : "",
            p.oem_direct_confirmed ? "OEM-direct purchasing confirmed — hardware channel competition present." : "",
            !p.channel_mismatch_flag && !p.incumbent_msp && !p.oem_direct_confirmed
              ? "No barriers identified — clean account access."
              : "",
            p.ce_name ? `Assigned CE: ${p.ce_name}.` : "",
          ].filter(Boolean).join(" ");

          const topOpps = crm?.top_opportunities ?? [];
          const penetrationPct = (penetrationRatio * 100).toFixed(1);
          const penetrationNote = wwtAddressableMid > 0
            ? `Pipeline penetration: ${penetrationPct}% of ${fmtUSD(wwtAddressableMid)} WWT addressable mid.`
            : "";
          const penetrationContext = penetrationRatio > 0.10
            ? "Strong strategic penetration — account well developed."
            : penetrationRatio > 0.03
            ? ""
            : penetrationRatio > 0.01
            ? "Early-stage relationship — expand from current engagement categories."
            : crm?.linked
            ? "Deal sizes suggest transactional access rather than strategic partnership — executive relationship development needed."
            : "";
          const warmthExpl = crm?.linked
            ? [
                pipe3yr > 0
                  ? `${fmtUSD(pipe3yr)} open pipeline (3yr), ${crm.open_opp_count ?? 0} open opportunities.`
                  : `CRM linked, $0 open pipeline (3yr).`,
                crm.sellers && crm.sellers.length > 0
                  ? `Primary seller${crm.sellers.slice(0, 3).length > 1 ? "s" : ""}: ${crm.sellers.slice(0, 3).join(", ")}.`
                  : "",
                won3yr > 0 ? `Closed won (3yr): ${fmtUSD(won3yr)}.` : "",
                topOpps.length > 0
                  ? `Top opportunities: ${topOpps.map(o => `${o.name} ${fmtUSD(o.amount)}`).join(", ")}.`
                  : "",
                penetrationNote,
                penetrationContext,
                p.ce_name ? `CE: ${p.ce_name}.` : "",
              ].filter(Boolean).join(" ")
            : [
                "CRM account not yet linked to this company record — pending manual review. Pipeline data unavailable.",
                p.ce_name ? `CE: ${p.ce_name} assigned.` : "",
              ].filter(Boolean).join(" ");

          const factors = [
            { label: "Tech Maturity",       score: techMaturity,     desc: `Score ${matScore}`,                                                              explanation: techExpl },
            { label: "Financial Capacity",  score: financialCap,     desc: p.revenue_ttm ? formatCap(p.revenue_ttm) + " rev" : "Unknown",                    explanation: finExpl },
            { label: "Strategic Urgency",   score: strategicUrgency, desc: `${urgencyCount} signal${urgencyCount !== 1 ? "s" : ""}`,                         explanation: urgencyExpl },
            { label: "WWT Accessibility",   score: accessibility,    desc: p.channel_mismatch_flag ? "Mismatch" : p.incumbent_msp ? `MSP: ${p.incumbent_msp}` : "Clean", explanation: accessExpl },
            { label: "Relationship Warmth", score: warmth,           desc: crm?.linked ? fmtUSD(pipe3yr) + " pipeline" : "No CRM link",                     explanation: warmthExpl },
          ];
          const total = factors.reduce((sum, f) => sum + f.score, 0);
          const barColor = (s: number) => s >= 4 ? "#16a34a" : s >= 3 ? "#f59e0b" : "#dc2626";

          // ── Total score narrative ───────────────────────────────────────────
          const maxFactor = factors.reduce((a, b) => a.score >= b.score ? a : b);
          const minFactor = factors.reduce((a, b) => a.score <= b.score ? a : b);
          const factorShortDesc: Record<string, string> = {
            "Tech Maturity": matScore >= 15
              ? `AI maturity score ${matScore} — high AI threshold confirmed, +5% addressable bonus applied`
              : `Signal score ${matScore} — ${15 - matScore} points below high AI maturity threshold`,
            "Financial Capacity": p.revenue_ttm ? `${formatCap(p.revenue_ttm)} TTM revenue` : "Revenue unknown",
            "Strategic Urgency": urgencyCount > 0
              ? `${urgencyCount} qualifying signals — ${sortedQS[0]?.signal_title ?? ""}`
              : "no active forcing functions — stable execution phase",
            "WWT Accessibility": !p.channel_mismatch_flag && !p.incumbent_msp
              ? "clean territory, no MSP incumbency"
              : p.channel_mismatch_flag && p.incumbent_msp
              ? `channel mismatch and MSP (${p.incumbent_msp}) — dual barriers`
              : p.channel_mismatch_flag ? "tech decisions outside WWT territory"
              : `incumbent MSP ${p.incumbent_msp} requires displacement`,
            "Relationship Warmth": crm?.linked
              ? `${fmtUSD(pipe3yr)} active pipeline (${penetrationPct}% penetration), ${crm.open_opp_count ?? 0} open opportunities`
              : "no CRM data — pending account link",
          };
          const hasAIOpps = crm?.top_opportunities?.some(o => /ai|glean|portal26|proving ground|cognition/i.test(o.name))
            || signals.some(s => /ai proving ground|glean|shadow ai/i.test(s.signal_title ?? ""));
          const aiOpp = crm?.top_opportunities?.find(o => /ai|glean|portal26|proving ground/i.test(o.name));
          const recommendedAction = (() => {
            if (p.incumbent_msp && aiOpp) {
              return `leverage active AI engagement (${aiOpp.name.slice(0, 60)}) to build strategic relationship for MSP displacement`;
            }
            if (p.incumbent_msp) {
              return `identify displacement opportunity — focus on categories outside MSP scope`;
            }
            if (strategicUrgency <= 2 && !hasAIOpps) {
              return `relationship-building posture now, positioned for next M&A or leadership transition event`;
            }
            if (hasAIOpps) {
              return `leverage existing AI Proving Ground engagement to expand into ${p.incumbent_msp ? "OT security" : "cloud modernization and OT security"} categories`;
            }
            return `expand from current ${crm?.linked ? "active" : "initial"} engagement into strategic infrastructure and AI categories`;
          })();
          const tierLabel = total >= 20 ? "Immediate Priority" : total >= 15 ? "Near-term Opportunity" : total >= 10 ? "Medium-term Watch" : "Low Near-term Priority";
          const narrative = `${tierLabel}. ${companyName} scores ${total}/25. Strongest signal: ${maxFactor.label} (${maxFactor.score}/5) — ${factorShortDesc[maxFactor.label] ?? ""}. Primary constraint: ${minFactor.label} (${minFactor.score}/5) — ${factorShortDesc[minFactor.label] ?? ""}. Recommended action: ${recommendedAction}.`;

          return (
            <div>
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {factors.map(f => (
                  <div key={f.label}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 500, color: "#374151" }}>{f.label}</span>
                      <span style={{ fontSize: 11, color: "#9ca3af" }}>{f.desc}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ flex: 1, height: 8, background: "#f3f4f6", borderRadius: 4, overflow: "hidden" }}>
                        <div style={{ width: `${(f.score / 5) * 100}%`, height: "100%", background: barColor(f.score), borderRadius: 4 }} />
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 700, color: barColor(f.score), minWidth: 24, textAlign: "right" }}>{f.score}/5</span>
                    </div>
                    <p style={{ marginTop: 4, marginBottom: 0, fontSize: 12, color: "#6B7280", lineHeight: 1.6 }}>{f.explanation}</p>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid #e5e7eb", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>Total Score</span>
                <span style={{ fontSize: 22, fontWeight: 800, color: total >= 20 ? "#16a34a" : total >= 15 ? "#f59e0b" : "#dc2626" }}>{total} / 25</span>
              </div>
              <p style={{ marginTop: 12, marginBottom: 0, fontSize: 12, color: "#6B7280", fontStyle: "italic", lineHeight: 1.6 }}>{narrative}</p>
            </div>
          );
        })() : (
          <p style={{ color: "#9ca3af", fontSize: 13 }}>Run estimate first to calculate opportunity score.</p>
        )}
      </div>

      {/* ── Leadership ── */}
      <div className="detail-section card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>Leadership Signals</h2>
          <button
            onClick={handleShowPast}
            style={{ padding: "4px 12px", borderRadius: 5, border: "1px solid #d1d5db", background: "#fff", fontSize: 12, cursor: "pointer", color: "#374151" }}
          >
            {showPast ? "Current only" : "Show past leaders"}
          </button>
        </div>

        {(() => {
          const allDates = [
            ...signals.map(s => s.signal_date || s.created_at?.slice(0, 10)),
            ...visibleLeaders.map(l => l.hire_date),
          ].filter(Boolean).map(d => new Date(d!).getTime()).filter(n => !isNaN(n));
          if (allDates.length === 0) return null;
          const daysSince = Math.floor((Date.now() - Math.max(...allDates)) / 86_400_000);
          if (daysSince <= 90) return null;
          return (
            <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 6, padding: "9px 14px", marginBottom: 14, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, color: "#d97706" }}>⚠</span>
              <span style={{ fontSize: 13, color: "#92400e" }}>Most recent signal is <strong>{daysSince} days old</strong> — consider refreshing intelligence data.</span>
            </div>
          );
        })()}
        {visibleLeaders.length === 0 ? (
          <p style={{ color: "#9ca3af", fontSize: 13 }}>No leadership data collected yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Role", "Name", "Location", "Hire Date", "Category", "Score"].map(h => (
                  <th key={h} style={{ padding: "6px 10px", textAlign: h === "Score" ? "right" : "left", fontSize: 11, fontWeight: 600, color: "#6b7280", textTransform: "uppercase", letterSpacing: "0.05em", borderBottom: "2px solid #e5e7eb" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleLeaders.map(l => (
                <tr key={l.id} style={{ opacity: l.is_current ? 1 : 0.55 }}>
                  <td style={tdL}>{l.role}</td>
                  <td style={tdL}>
                    {l.linkedin_url
                      ? <a href={l.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb" }}>{l.person_name ?? "—"}</a>
                      : (l.person_name ?? <span style={{ color: "#9ca3af" }}>—</span>)}
                  </td>
                  <td style={tdL}>{[l.location_city, l.location_country].filter(Boolean).join(", ") || <span style={{ color: "#9ca3af" }}>—</span>}</td>
                  <td style={tdL}>{l.hire_date ?? <span style={{ color: "#9ca3af" }}>—</span>}</td>
                  <td style={tdL}>
                    {l.spend_category
                      ? <span style={{ background: "#f3f4f6", borderRadius: 4, padding: "1px 7px", fontSize: 11, fontWeight: 600, color: "#374151" }}>{l.spend_category}</span>
                      : <span style={{ color: "#9ca3af" }}>—</span>}
                  </td>
                  <td style={{ ...tdL, textAlign: "right", fontWeight: 600, color: l.signal_score > 0 ? "#2563eb" : "#9ca3af" }}>
                    {l.signal_score ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Signals feed ── */}
      <div className="detail-section card">
        <h2 style={{ marginBottom: 14 }}>Recent Signals</h2>

        {signals.length === 0 ? (
          <p style={{ color: "#9ca3af", fontSize: 13 }}>No signals collected yet — first batch enrichment will populate this.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {signals.map((s, i) => (
              <div key={s.id} style={{ padding: "12px 4px", borderBottom: i < signals.length - 1 ? "1px solid #f3f4f6" : undefined, display: "flex", flexDirection: "column", gap: 5 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <SignalTypeBadge type={s.signal_type} />
                  {s.signal_category && (
                    <span style={{ background: "#f3f4f6", borderRadius: 4, padding: "2px 7px", fontSize: 11, fontWeight: 600, color: "#374151" }}>
                      {s.signal_category}
                    </span>
                  )}
                  <DirectionIcon dir={s.spend_impact_direction} />
                  <span style={{ fontSize: 12, color: "#9ca3af", marginLeft: "auto" }}>{s.signal_date ?? s.created_at?.slice(0, 10) ?? ""}</span>
                  {s.signal_url && (
                    <a href={s.signal_url} target="_blank" rel="noopener noreferrer" style={{ color: "#6b7280", fontSize: 14, lineHeight: 1 }} title="Source">&#x1F517;</a>
                  )}
                </div>
                {s.signal_title && (
                  <div style={{ fontSize: 13, color: "#1a1a2e", fontWeight: 500 }}>{s.signal_title}</div>
                )}
                {s.signal_description && (
                  <div style={{ fontSize: 12, color: "#6b7280", lineHeight: 1.5 }}>
                    {s.signal_description.length > 200 ? s.signal_description.slice(0, 200) + "…" : s.signal_description}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CompanyDetail() {
  const { id, ticker } = useParams<{ id?: string; ticker?: string }>();
  const navigate = useNavigate();
  const [company, setCompany] = useState<CompanyDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"overview" | "intelligence">("overview");
  const [showEdit, setShowEdit] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  function reload() {
    if (!company) return;
    const req = company.ticker
      ? fetchCompanyByTicker(company.ticker)
      : fetchCompany(company.id);
    req.then(setCompany).catch(() => null);
  }

  useEffect(() => {
    setLoading(true);
    setError(null);
    const req = ticker
      ? fetchCompanyByTicker(ticker)
      : id
      ? fetchCompany(Number(id))
      : Promise.reject(new Error("No company identifier"));
    req
      .then(setCompany)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id, ticker]);

  async function handleDelete() {
    if (!company) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteCompany(company.id);
      navigate("/companies");
    } catch (e: unknown) {
      setDeleteError(e instanceof Error ? e.message : "Delete failed");
      setDeleting(false);
    }
  }

  function handleSaved() {
    setShowEdit(false);
    setToast("Changes saved");
    setTimeout(() => setToast(null), 3500);
    reload();
  }

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="page-body"><div className="error">{error}</div></div>;
  if (!company) return null;

  const sortedFinancials = [...company.financials]
    .sort((a, b) => b.snapshot_date.localeCompare(a.snapshot_date))
    .slice(0, 30);

  const sortedEvents = [...company.events].sort(
    (a, b) => (b.event_date ?? b.created_at).localeCompare(a.event_date ?? a.created_at)
  );

  return (
    <>
      {toast && (
        <div style={{ position: "fixed", bottom: 24, right: 24, background: "#16a34a", color: "#fff", padding: "12px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600, boxShadow: "0 4px 16px rgba(0,0,0,0.2)", zIndex: 2000 }}>
          {toast}
        </div>
      )}
      {showEdit && (
        <EditCompanyModal company={company} onClose={() => setShowEdit(false)} onSaved={handleSaved} />
      )}
      <div className="page-header">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
          <h1>{company.name}</h1>
          {company.ticker && (
            <span className="ticker-badge">{company.ticker}</span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {company.supply_chain_position && (
            <span className="badge badge-supply-chain">{company.supply_chain_position}</span>
          )}
          {company.industry && (
            <span className="badge badge-segment">{company.industry}</span>
          )}
          <button onClick={() => setShowEdit(true)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", fontSize: 13, cursor: "pointer", fontWeight: 500 }}>
            Edit
          </button>
          {!confirmDelete ? (
            <button onClick={() => setConfirmDelete(true)} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #fca5a5", background: "#fef2f2", color: "#dc2626", fontSize: 13, cursor: "pointer", fontWeight: 500 }}>
              Delete
            </button>
          ) : (
            <span style={{ display: "flex", alignItems: "center", gap: 6, background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: "4px 10px" }}>
              <span style={{ fontSize: 13, color: "#991b1b", fontWeight: 600 }}>Delete {company.name}?</span>
              <button onClick={handleDelete} disabled={deleting} style={{ padding: "4px 10px", borderRadius: 5, border: "none", background: "#dc2626", color: "#fff", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                {deleting ? "Deleting…" : "Confirm"}
              </button>
              <button onClick={() => { setConfirmDelete(false); setDeleteError(null); }} style={{ padding: "4px 8px", borderRadius: 5, border: "none", background: "transparent", fontSize: 13, cursor: "pointer", color: "#6b7280" }}>✕</button>
            </span>
          )}
        </div>
      </div>
      {deleteError && <div className="page-body" style={{ paddingBottom: 0 }}><div className="error">{deleteError}</div></div>}

      <div className="page-body">
        <div className="stat-grid">
          <div className="stat-card">
            <div className="label">Market Cap</div>
            <div className="value">{formatCap(company.latest_market_cap)}</div>
          </div>
          <div className="stat-card">
            <div className="label">Price (USD)</div>
            <div className="value">{formatPrice(company.latest_price)}</div>
          </div>
          <div className="stat-card">
            <div className="label">Q Revenue{company.latest_quarter_label ? ` (${company.latest_quarter_label})` : ""}</div>
            <div className="value">{formatCap(company.latest_quarterly_revenue)}</div>
          </div>
          <div className="stat-card">
            <div className="label">
              FY Revenue{company.latest_fiscal_year_label ? ` (${company.latest_fiscal_year_label})` : ""}
              {company.revenue_manually_set && <span title="Revenue locked — manually verified" style={{ marginLeft: 5, fontSize: 12 }}>🔒</span>}
            </div>
            <div className="value">{formatCap(company.latest_revenue)}</div>
          </div>
        </div>

        {company.status && company.status !== "Active" && company.status !== "Unknown" && (
          <div className="card acquisition-banner" style={{
            borderLeft: `4px solid ${
              company.status === "Acquired" ? "#dc2626" :
              company.status === "Merged" ? "#ea580c" :
              company.status === "Sanctioned" ? "#7c3aed" :
              "#6b7280"
            }`,
            marginBottom: 20,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: company.acquired_by || company.acquisition_notes ? 8 : 0 }}>
              <span className="status-badge" style={{
                background: company.status === "Acquired" ? "#fef2f2" : company.status === "Merged" ? "#fff7ed" : company.status === "Sanctioned" ? "#f5f3ff" : "#f3f4f6",
                color: company.status === "Acquired" ? "#dc2626" : company.status === "Merged" ? "#ea580c" : company.status === "Sanctioned" ? "#7c3aed" : "#6b7280",
                fontSize: 11,
              }}>
                {company.status.toUpperCase()}
              </span>
              <span style={{ fontWeight: 600, fontSize: 14 }}>
                {company.status === "Acquired" ? "This company has been acquired" :
                 company.status === "Merged" ? "This company has merged" :
                 company.status === "Delisted" ? "This company has been delisted" :
                 company.status === "Sanctioned" ? "Trading sanctioned / suspended" :
                 company.status}
              </span>
            </div>
            {company.acquired_by && (
              <div style={{ fontSize: 13, color: "#374151" }}>
                <strong>Acquirer:</strong> {company.acquired_by}
              </div>
            )}
            {company.acquisition_notes && (
              <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>
                {company.acquisition_notes}
              </div>
            )}
          </div>
        )}

        {/* Tab bar */}
        <div style={{ display: "flex", borderBottom: "2px solid #e5e7eb", marginBottom: 20, gap: 0 }}>
          {(["overview", "intelligence"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "10px 22px", border: "none", background: "none", cursor: "pointer", fontSize: 14,
              fontWeight: tab === t ? 700 : 400,
              color: tab === t ? "#2563eb" : "#6b7280",
              borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
              marginBottom: -2, textTransform: "capitalize",
            }}>
              {t}
            </button>
          ))}
        </div>

        {tab === "intelligence" && company && (
          <IntelligenceTab companyId={company.id} companyName={company.name} />
        )}

        {tab === "overview" && <div className="detail-grid">
          <div>
            <div className="detail-section card">
              <h2>Company Info</h2>
              <dl className="detail-kv">
                <dt>Energy Value Chain</dt>
                <dd>
                  {company.supply_chain_position
                    ? <span className="badge badge-supply-chain">{company.supply_chain_position}</span>
                    : "—"}
                </dd>
                <dt>Energy Industry</dt>
                <dd>{company.industry ?? "—"}</dd>
                <dt>Country</dt>
                <dd>{company.country ?? "—"}</dd>
                <dt>Exchange</dt>
                <dd>{company.exchange ?? "—"}</dd>
                <dt>Website</dt>
                <dd>
                  {company.website
                    ? <a href={company.website} target="_blank" rel="noopener noreferrer">{company.website}</a>
                    : "—"}
                </dd>
                <dt>Category</dt>
                <dd>{company.energy_category ?? "—"}</dd>
                <dt>Maturity</dt>
                <dd>{company.energy_maturity ?? "—"}</dd>
                <dt>WWT Territory</dt>
                <dd>{company.wwt_territory ?? "—"}</dd>
                <dt>WWT Model</dt>
                <dd>{company.wwt_model ?? "—"}</dd>
                {company.ce_name && <>
                  <dt>Client Executive</dt>
                  <dd>{company.ce_name}</dd>
                  {company.ce_email && <>
                    <dt>CE Email</dt>
                    <dd><a href={`mailto:${company.ce_email}`} style={{ color: "#2563eb" }}>{company.ce_email}</a></dd>
                  </>}
                  {company.ce_phone && <>
                    <dt>CE Phone</dt>
                    <dd>{company.ce_phone}</dd>
                  </>}
                </>}
              </dl>
              {company.description && (
                <p style={{ marginTop: 14, fontSize: 13, color: "#4b5563", lineHeight: 1.6 }}>
                  {company.description}
                </p>
              )}
            </div>

            <div className="detail-section card" style={{ marginTop: 16 }}>
              <h2>Financial History</h2>
              {sortedFinancials.length === 0 ? (
                <p style={{ color: "#9ca3af", fontSize: 13 }}>No financial snapshots yet.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th style={{ textAlign: "right" }}>Price</th>
                      <th style={{ textAlign: "right" }}>Market Cap</th>
                      <th style={{ textAlign: "right" }}>Q Revenue</th>
                      <th style={{ textAlign: "right" }}>FY Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedFinancials.map((f) => (
                      <tr key={f.id}>
                        <td>{f.snapshot_date}</td>
                        <td style={{ textAlign: "right" }}>{formatPrice(f.price_usd)}</td>
                        <td style={{ textAlign: "right" }}>{formatCap(f.market_cap_usd)}</td>
                        <td style={{ textAlign: "right" }}>
                          {f.revenue_quarterly_usd ? `${formatCap(f.revenue_quarterly_usd)}${f.revenue_quarter_label ? ` ${f.revenue_quarter_label}` : ""}` : "—"}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          {f.revenue_annual_usd ? `${formatCap(f.revenue_annual_usd)}${f.revenue_fiscal_year_label ? ` ${f.revenue_fiscal_year_label}` : ""}` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>

          <div>
            <div className="detail-section card">
              <h2>Events</h2>
              {sortedEvents.length === 0 ? (
                <p style={{ color: "#9ca3af", fontSize: 13 }}>No events recorded yet.</p>
              ) : (
                sortedEvents.map((e) => (
                  <div key={e.id} className="event-item">
                    <div className="event-meta">
                      <span className="badge badge-model" style={{ marginRight: 6 }}>{e.event_type}</span>
                      {e.event_date ?? "—"}
                    </div>
                    {e.source_url
                      ? <a href={e.source_url} target="_blank" rel="noopener noreferrer" className="event-title">{e.title}</a>
                      : <div className="event-title">{e.title}</div>}
                    {e.summary && (
                      <div className="event-summary">
                        {e.summary.slice(0, 300)}{e.summary.length > 300 ? "…" : ""}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>}
      </div>
    </>
  );
}
