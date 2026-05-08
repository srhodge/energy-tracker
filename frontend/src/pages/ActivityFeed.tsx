import { useEffect, useState } from "react";
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

export default function ActivityFeed() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchNews(100)
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Activity Feed</h1>
      </div>
      <div className="page-body">
        {error && <div className="error">{error}</div>}

        <div className="card">
          {loading ? (
            <div className="loading">Loading...</div>
          ) : items.length === 0 ? (
            <p style={{ color: "#9ca3af", padding: "16px 0" }}>No news yet — scraper runs every 6 hours.</p>
          ) : (
            items.map((item) => {
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
                      <Link
                        to={`/company/${item.company_ticker}`}
                        className="news-company-tag"
                      >
                        {item.company_ticker}
                      </Link>
                    )}
                  </div>
                  {item.source_url ? (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="news-headline"
                    >
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
