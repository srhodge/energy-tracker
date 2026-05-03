import { useEffect, useState } from "react";
import { fetchTerritoryRollup } from "../api/client";
import type { TerritoryRollup } from "../types";
import { formatCap } from "../components/FormatCap";

export default function TerritoryDashboard() {
  const [rows, setRows] = useState<TerritoryRollup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTerritoryRollup()
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const maxCap = rows.reduce((m, r) => Math.max(m, r.total_market_cap_usd ?? 0), 0);
  const totalCap = rows.reduce((s, r) => s + (r.total_market_cap_usd ?? 0), 0);
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
                    <th style={{ width: 200 }}>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const pct = maxCap > 0 ? ((r.total_market_cap_usd ?? 0) / maxCap) * 100 : 0;
                    return (
                      <tr key={r.wwt_territory}>
                        <td><strong>{r.wwt_territory}</strong></td>
                        <td style={{ textAlign: "right" }}>{r.company_count}</td>
                        <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCap(r.total_market_cap_usd)}</td>
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
