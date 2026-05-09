import { useEffect, useRef, useState, useMemo } from "react";
import {
  Chart as ChartJS,
  LogarithmicScale,
  PointElement,
  Tooltip,
  Legend,
  type ChartData,
  type ChartOptions,
  type Plugin,
  type BubbleDataPoint,
} from "chart.js";
import { Bubble } from "react-chartjs-2";
import { fetchScatterData } from "../api/client";
import type { ScatterPoint } from "../types";

ChartJS.register(LogarithmicScale, PointElement, Tooltip, Legend);

const COLORS: Record<string, string> = {
  Upstream:       "#f97316",
  Midstream:      "#3b82f6",
  Downstream:     "#22c55e",
  Integrated:     "#8b5cf6",
  Petrochemicals: "#eab308",
  Services:       "#6b7280",
};
const DEFAULT_COLOR = "#94a3b8";

function fmt(v: number): string {
  if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

function bubbleR(revUsd: number): number {
  return Math.max(4, Math.min(20, Math.sqrt(revUsd / 1e9) * 1.8));
}

function median(vals: number[]): number {
  if (!vals.length) return 0;
  const sorted = [...vals].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

type PSFilter = "all" | "under1" | "1to3" | "over3";

interface BubbleDatum extends BubbleDataPoint {
  name: string;
  ticker?: string;
  fy?: string;
  ps: number;
}

// Custom plugin: draws the P/S = 1x dashed diagonal on the canvas
const psReferenceLinePlugin: Plugin<"bubble"> = {
  id: "psReferenceLine",
  afterDatasetsDraw(chart) {
    const xScale = chart.scales["x"];
    const yScale = chart.scales["y"];
    if (!xScale || !yScale) return;
    const { ctx } = chart;

    // Draw the line from ($10M, $10M) to ($1T, $1T)
    const pts: [number, number][] = [
      [1e7, 1e7], [1e8, 1e8], [1e9, 1e9], [1e10, 1e10], [1e11, 1e11], [1e12, 1e12],
    ];

    ctx.save();
    ctx.beginPath();
    ctx.setLineDash([6, 4]);
    ctx.strokeStyle = "rgba(100,116,139,0.5)";
    ctx.lineWidth = 1.5;

    let first = true;
    for (const [x, y] of pts) {
      const px = xScale.getPixelForValue(x);
      const py = yScale.getPixelForValue(y);
      if (first) { ctx.moveTo(px, py); first = false; }
      else ctx.lineTo(px, py);
    }
    ctx.stroke();
    ctx.restore();
  },
};

export default function Analytics() {
  const [data, setData] = useState<{ total: number; included: number; items: ScatterPoint[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [posFilter, setPosFilter] = useState("all");
  const [psFilter, setPsFilter] = useState<PSFilter>("all");
  const [terrFilter, setTerrFilter] = useState("all");
  const chartRef = useRef<ChartJS<"bubble">>(null);

  useEffect(() => {
    fetchScatterData()
      .then(d => setData({ total: d.total_companies, included: d.included_count, items: d.items }))
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  const positions = useMemo(() => {
    if (!data) return [];
    return Array.from(
      new Set(data.items.map(c => c.supply_chain_position).filter((p): p is string => !!p))
    ).sort();
  }, [data]);

  const territories = useMemo(() => {
    if (!data) return [];
    return Array.from(
      new Set(data.items.map(c => c.territory).filter((t): t is string => !!t))
    ).sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.items.filter(c => {
      if (terrFilter !== "all" && c.territory !== terrFilter) return false;
      if (posFilter !== "all" && c.supply_chain_position !== posFilter) return false;
      const ps = c.market_cap_usd / c.revenue_annual_usd;
      if (psFilter === "under1" && ps >= 1) return false;
      if (psFilter === "1to3" && (ps < 1 || ps > 3)) return false;
      if (psFilter === "over3" && ps <= 3) return false;
      return true;
    });
  }, [data, terrFilter, posFilter, psFilter]);

  const metrics = useMemo(() => {
    const psRatios = filtered.map(c => c.market_cap_usd / c.revenue_annual_usd);
    return {
      count: filtered.length,
      medianPS: median(psRatios),
      under1: psRatios.filter(p => p < 1).length,
      over3: psRatios.filter(p => p > 3).length,
    };
  }, [filtered]);

  const chartData = useMemo((): ChartData<"bubble", BubbleDatum[]> => {
    const groups: Record<string, BubbleDatum[]> = {};
    for (const c of filtered) {
      const pos = c.supply_chain_position ?? "Other";
      if (!groups[pos]) groups[pos] = [];
      groups[pos].push({
        x: c.revenue_annual_usd,
        y: c.market_cap_usd,
        r: bubbleR(c.revenue_annual_usd),
        name: c.name,
        ticker: c.ticker ?? undefined,
        fy: c.revenue_fiscal_year_label ?? undefined,
        ps: c.market_cap_usd / c.revenue_annual_usd,
      });
    }
    return {
      datasets: Object.entries(groups).map(([pos, pts]) => ({
        label: pos,
        data: pts,
        backgroundColor: (COLORS[pos] ?? DEFAULT_COLOR) + "bb",
        borderColor: COLORS[pos] ?? DEFAULT_COLOR,
        borderWidth: 1,
      })),
    };
  }, [filtered]);

  const options = useMemo((): ChartOptions<"bubble"> => ({
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "logarithmic",
        title: { display: true, text: "Annual Revenue (USD)", font: { size: 12 }, color: "#6b7280" },
        ticks: { color: "#6b7280", callback: (v) => fmt(Number(v)) },
        grid: { color: "#f0f2f5" },
      },
      y: {
        type: "logarithmic",
        title: { display: true, text: "Market Cap (USD)", font: { size: 12 }, color: "#6b7280" },
        ticks: { color: "#6b7280", callback: (v) => fmt(Number(v)) },
        grid: { color: "#f0f2f5" },
      },
    },
    plugins: {
      legend: {
        position: "bottom",
        labels: { font: { size: 12 }, padding: 16, usePointStyle: true, pointStyleWidth: 10 },
      },
      tooltip: {
        callbacks: {
          title: () => "",
          label: (ctx) => {
            const d = ctx.raw as BubbleDatum;
            if (!d.name) return "";
            return [
              `${d.name}${d.ticker ? ` (${d.ticker})` : ""}`,
              `Revenue: ${fmt(d.x as number)}${d.fy ? ` ${d.fy}` : ""}`,
              `Market Cap: ${fmt(d.y as number)}`,
              `P/S: ${d.ps.toFixed(1)}x`,
            ];
          },
        },
        backgroundColor: "#1e293b",
        padding: 10,
        cornerRadius: 8,
        bodyFont: { size: 12 },
        bodySpacing: 4,
      },
    },
  }), []);

  const selectStyle: React.CSSProperties = {
    padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
    fontSize: 13, background: "#fff", color: "#1a1a2e", cursor: "pointer",
  };

  return (
    <>
      <div className="page-header" style={{ justifyContent: "space-between" }}>
        <div>
          <h1>Analytics</h1>
          {data && (
            <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
              {data.included} of {data.total} companies have sufficient data for analysis
            </div>
          )}
        </div>
      </div>

      <div className="page-body">
        {loading && <div className="loading">Loading…</div>}

        {!loading && data && (
          <>
            {/* ── Section: Revenue vs Market Cap ── */}
            <div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e" }}>Revenue vs market cap</div>
                <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                  Bubble size = revenue. Dashed line = P/S ratio of 1x.
                </div>
              </div>

              {/* Metric cards */}
              <div className="stat-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 20 }}>
                <div className="stat-card">
                  <div className="label">Companies shown</div>
                  <div className="value">{metrics.count}</div>
                </div>
                <div className="stat-card">
                  <div className="label">Median P/S ratio</div>
                  <div className="value">{metrics.medianPS.toFixed(1)}x</div>
                </div>
                <div className="stat-card">
                  <div className="label">P/S under 1x</div>
                  <div className="value">{metrics.under1}</div>
                  <div className="sub">potentially undervalued</div>
                </div>
                <div className="stat-card">
                  <div className="label">P/S over 3x</div>
                  <div className="value">{metrics.over3}</div>
                  <div className="sub">growth premium</div>
                </div>
              </div>

              {/* Filters */}
              <div className="filter-bar" style={{ marginBottom: 16 }}>
                <select style={selectStyle} value={terrFilter} onChange={e => setTerrFilter(e.target.value)}>
                  <option value="all">All territories</option>
                  {territories.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select style={selectStyle} value={posFilter} onChange={e => setPosFilter(e.target.value)}>
                  <option value="all">All value chains</option>
                  {positions.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <select style={selectStyle} value={psFilter} onChange={e => setPsFilter(e.target.value as PSFilter)}>
                  <option value="all">All P/S ratios</option>
                  <option value="under1">Under 1x</option>
                  <option value="1to3">1x – 3x</option>
                  <option value="over3">Over 3x</option>
                </select>
              </div>

              {/* Chart */}
              <div className="card" style={{ padding: 24 }}>
                <div style={{ height: 520 }}>
                  {filtered.length > 0 ? (
                    <Bubble
                      ref={chartRef}
                      data={chartData}
                      options={options}
                      plugins={[psReferenceLinePlugin]}
                    />
                  ) : (
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "center",
                      height: "100%", color: "#9ca3af", fontSize: 14,
                    }}>
                      No companies match the selected filters.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Divider — future sections below */}
            <hr style={{ margin: "32px 0", border: "none", borderTop: "1px solid #e0e4ea" }} />
          </>
        )}
      </div>
    </>
  );
}
