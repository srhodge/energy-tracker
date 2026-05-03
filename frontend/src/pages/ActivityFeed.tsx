import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchEvents } from "../api/client";
import type { EventWithCompany, EventType } from "../types";

const EVENT_TYPES: { value: EventType | ""; label: string }[] = [
  { value: "", label: "All types" },
  { value: "news", label: "News" },
  { value: "project", label: "Project" },
  { value: "earnings", label: "Earnings" },
  { value: "filing", label: "Filing" },
];

export default function ActivityFeed() {
  const [events, setEvents] = useState<EventWithCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventType, setEventType] = useState<EventType | "">("");

  useEffect(() => {
    setLoading(true);
    fetchEvents({ event_type: eventType || undefined, limit: 100 })
      .then(setEvents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [eventType]);

  return (
    <>
      <div className="page-header">
        <h1>Activity Feed</h1>
      </div>
      <div className="page-body">
        <div className="filter-bar" style={{ marginBottom: 16 }}>
          <select value={eventType} onChange={(e) => setEventType(e.target.value as EventType | "")}>
            {EVENT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="card">
          {loading ? (
            <div className="loading">Loading...</div>
          ) : events.length === 0 ? (
            <p style={{ color: "#9ca3af", padding: "16px 0" }}>No events yet. Run the news scraper to populate this feed.</p>
          ) : (
            events.map((e) => (
              <div key={e.id} className="event-item">
                <div className="event-meta">
                  <span className="badge badge-model" style={{ marginRight: 6 }}>{e.event_type}</span>
                  <Link to={`/companies/${e.company_id}`} style={{ color: "#374151", fontWeight: 500 }}>
                    {e.company_name}
                    {e.company_ticker ? ` (${e.company_ticker})` : ""}
                  </Link>
                  {" · "}
                  {e.event_date ?? "—"}
                </div>
                {e.source_url
                  ? <a href={e.source_url} target="_blank" rel="noopener noreferrer" className="event-title">{e.title}</a>
                  : <div className="event-title">{e.title}</div>}
                {e.summary && (
                  <div className="event-summary">{e.summary.slice(0, 250)}{e.summary.length > 250 ? "…" : ""}</div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
