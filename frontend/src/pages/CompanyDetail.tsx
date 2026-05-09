import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchCompany, fetchCompanyByTicker, updateCompany, deleteCompany, setRevenue } from "../api/client";
import type { CompanyDetail as CompanyDetailType, CompanyUpdateRequest, ValueChainPosition, CompanyStatus } from "../types";
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

export default function CompanyDetail() {
  const { id, ticker } = useParams<{ id?: string; ticker?: string }>();
  const navigate = useNavigate();
  const [company, setCompany] = useState<CompanyDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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

        <div className="detail-grid">
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
        </div>
      </div>
    </>
  );
}
