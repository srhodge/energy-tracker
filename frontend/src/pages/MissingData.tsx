import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchMissingData } from "../api/client";
import type { MissingDataResult, MissingDataStub } from "../api/client";

const SECTIONS: { key: keyof MissingDataResult; label: string; color: string }[] = [
  { key: "missing_all",      label: "Missing All Fields",    color: "#ef4444" },
  { key: "missing_website",  label: "Missing Website",       color: "#f97316" },
  { key: "missing_industry", label: "Missing Industry",      color: "#eab308" },
  { key: "missing_revenue",  label: "Missing Revenue",       color: "#6366f1" },
];

function CompanyTable({ rows }: { rows: MissingDataStub[] }) {
  if (rows.length === 0) {
    return <p style={{ color: "#6b7280", padding: "8px 0 4px" }}>None — all good.</p>;
  }
  return (
    <table className="company-table" style={{ marginTop: 8 }}>
      <thead>
        <tr>
          <th style={{ textAlign: "left" }}>Company</th>
          <th style={{ textAlign: "left" }}>Ticker</th>
          <th style={{ textAlign: "left" }}>Country</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((c) => (
          <tr key={c.id}>
            <td>
              <Link to={`/companies/${c.id}`} style={{ color: "#60a5fa" }}>
                {c.name}
              </Link>
            </td>
            <td style={{ color: "#9ca3af", fontFamily: "monospace" }}>{c.ticker ?? "—"}</td>
            <td style={{ color: "#9ca3af" }}>{c.country ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function MissingData() {
  const [data, setData] = useState<MissingDataResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMissingData()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Missing Data</h1>
        <span style={{ color: "#6b7280", fontSize: 14 }}>Active companies only — acquired/merged/delisted excluded</span>
      </div>
      <div className="page-body">
        {error && <div className="error">{error}</div>}
        {loading && <div className="loading">Loading...</div>}

        {data && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {SECTIONS.map(({ key, label, color }) => (
              <div key={key} className="card">
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <h2 style={{ margin: 0, fontSize: 16 }}>{label}</h2>
                  <span
                    style={{
                      background: color,
                      color: "#fff",
                      borderRadius: 9999,
                      padding: "2px 10px",
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {data[key].length}
                  </span>
                </div>
                <CompanyTable rows={data[key]} />
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
