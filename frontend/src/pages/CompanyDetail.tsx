import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchCompany } from "../api/client";
import type { CompanyDetail as CompanyDetailType } from "../types";
import { formatCap, formatPrice } from "../components/FormatCap";

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const [company, setCompany] = useState<CompanyDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchCompany(Number(id))
      .then(setCompany)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="loading">Loading...</div>;
  if (error) return <div className="page-body"><div className="error">{error}</div></div>;
  if (!company) return null;

  const sortedFinancials = [...company.financials].sort(
    (a, b) => b.snapshot_date.localeCompare(a.snapshot_date)
  ).slice(0, 30);

  const sortedEvents = [...company.events].sort(
    (a, b) => (b.event_date ?? b.created_at).localeCompare(a.event_date ?? a.created_at)
  );

  return (
    <>
      <div className="page-header">
        <div>
          <Link to="/" className="back-link">← Companies</Link>
          <h1>{company.name}</h1>
        </div>
        {company.ticker && (
          <span style={{ fontFamily: "monospace", background: "#f0f2f5", padding: "4px 10px", borderRadius: 4, fontSize: 15 }}>
            {company.ticker}
          </span>
        )}
      </div>

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
            <div className="label">WWT Territory</div>
            <div className="value" style={{ fontSize: 18 }}>{company.wwt_territory ?? "—"}</div>
            <div className="sub">{company.wwt_model ?? ""}</div>
          </div>
          <div className="stat-card">
            <div className="label">Value Chain</div>
            <div className="value" style={{ fontSize: 18 }}>{company.value_chain_position ?? "—"}</div>
            <div className="sub">{company.energy_segment ?? ""}</div>
          </div>
        </div>

        <div className="detail-grid">
          <div>
            <div className="detail-section card">
              <h2>Company Info</h2>
              <dl className="detail-kv">
                <dt>Country</dt><dd>{company.country ?? "—"}</dd>
                <dt>Exchange</dt><dd>{company.exchange ?? "—"}</dd>
                <dt>Website</dt>
                <dd>
                  {company.website
                    ? <a href={company.website} target="_blank" rel="noopener noreferrer">{company.website}</a>
                    : "—"}
                </dd>
                <dt>Category</dt><dd>{company.energy_category ?? "—"}</dd>
                <dt>Maturity</dt><dd>{company.energy_maturity ?? "—"}</dd>
              </dl>
              {company.description && (
                <p style={{ marginTop: 14, fontSize: 13, color: "#4b5563", lineHeight: 1.6 }}>{company.description}</p>
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
                    </tr>
                  </thead>
                  <tbody>
                    {sortedFinancials.map((f) => (
                      <tr key={f.id}>
                        <td>{f.snapshot_date}</td>
                        <td style={{ textAlign: "right" }}>{formatPrice(f.price_usd)}</td>
                        <td style={{ textAlign: "right" }}>{formatCap(f.market_cap_usd)}</td>
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
                    {e.summary && <div className="event-summary">{e.summary.slice(0, 300)}{e.summary.length > 300 ? "…" : ""}</div>}
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
