import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { fetchNews } from "../api/client";
import type { NewsItem } from "../types";

function timeAgo(iso?: string): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const SOURCE_COLORS: Record<string, string> = {
  "Reuters": "#f97316",
  "OilPrice.com": "#0ea5e9",
};

const SEL: React.CSSProperties = {
  padding: "5px 10px", border: "1px solid #d1d5db", borderRadius: 6,
  fontSize: 13, background: "#fff", color: "#1a1a2e", cursor: "pointer",
};

export default function ActivityFeed() {
  const [items, setItems]           = useState<NewsItem[]>([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);
  const [search, setSearch]         = useState("");
  const [sourceFilter, setSource]   = useState("");
  const [tickerFilter, setTicker]   = useState("");

  useEffect(() => {
    setLoading(true);
    fetchNews(200)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const sources = useMemo(
    () => Array.from(new Set(items.map(i => i.source).filter(Boolean))).sort() as string[],
    [items]
  );

  const filtered = useMemo(() => {
    let result = items;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(i => i.headline.toLowerCase().includes(q));
    }
    if (sourceFilter) {
      result = result.filter(i => i.source === sourceFilter);
    }
    if (tickerFilter.trim()) {
      const q = tickerFilter.toLowerCase();
      result = result.filter(i => i.company_ticker?.toLowerCase().includes(q));
    }
    return result;
  }, [items, search, sourceFilter, tickerFilter]);

  const anyFilterActive = !!(search || sourceFilter || tickerFilter);

  function handleReset() { setSearch(""); setSource(""); setTicker(""); }

  return (
    <>
      {/* Fixed filter bar */}
      <div style={{
        position: "fixed", top: 0, left: 220, right: 0, zIndex: 200,
        background: "#1a1a2e", borderBottom: "1px solid rgba(255,255,255,0.1)",
        padding: "6px 28px", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap",
      }}>
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)", marginRight: 8, whiteSpace: "nowrap" }}>Filters</span>
        <input
          type="search" placeholder="Search headlines…" value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ ...SEL, minWidth: 220 }}
        />
        <select value={sourceFilter} onChange={e => setSource(e.target.value)} style={SEL}>
          <option value="">All Sources</option>
          {sources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input
          type="search" placeholder="Filter by ticker…" value={tickerFilter}
          onChange={e => setTicker(e.target.value)}
          style={{ ...SEL, width: 160, fontFamily: "monospace" }}
        />
        {anyFilterActive && (
          <button onClick={handleReset} style={{
            padding: "5px 10px", border: "1px solid #d1d5db", borderRadius: 6,
            fontSize: 13, background: "#fff", color: "#6b7280", cursor: "pointer",
            display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap",
          }}>
            ↺ Reset
          </button>
        )}
      </div>

      <div className="page-header" style={{ paddingTop: 44 }}>
        <h1>Activity Feed</h1>
        {!loading && (
          <span style={{ fontSize: 13, color: "#6b7280" }}>
            {filtered.length} {anyFilterActive ? `of ${items.length} ` : ""}articles
          </span>
        )}
      </div>

      <div className="page-body">
        {error && <div className="error">{error}</div>}

        <div className="card">
          {loading ? (
            <div className="loading">Loading...</div>
          ) : filtered.length === 0 ? (
            <p style={{ color: "#9ca3af", padding: "16px 0" }}>
              {anyFilterActive ? "No articles match the current filters." : "No news yet — scraper runs every 6 hours."}
            </p>
          ) : (
            filtered.map((item) => {
              const color = item.source ? (SOURCE_COLORS[item.source] ?? "#6b7280") : "#6b7280";
              return (
                <div key={item.id} className="news-item">
                  <div className="news-meta">
                    {item.source && (
                      <span className="news-source-badge" style={{ background: color }}>
                        {item.source}
                      </span>
                    )}
                    <span className="news-time">{timeAgo(item.published_at)}</span>
                    {item.company_ticker && (
                      <Link to={`/company/${item.company_ticker}`} className="news-company-tag">
                        {item.company_ticker}
                      </Link>
                    )}
                  </div>
                  {item.source_url ? (
                    <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="news-headline">
                      {item.headline}
                    </a>
                  ) : (
                    <div className="news-headline">{item.headline}</div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}
