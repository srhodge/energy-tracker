import { useEffect, useRef, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Chart as ChartJS,
  LogarithmicScale,
  LinearScale,
  CategoryScale,
  BarElement,
  PointElement,
  Tooltip,
  Legend,
  type ChartData,
  type ChartOptions,
  type Plugin,
  type BubbleDataPoint,
} from "chart.js";
import { Bubble, Bar } from "react-chartjs-2";
import { fetchScatterData } from "../api/client";
import type { ScatterPoint } from "../types";

ChartJS.register(LogarithmicScale, LinearScale, CategoryScale, BarElement, PointElement, Tooltip, Legend);

const COLORS: Record<string, string> = {
  Upstream:       "#f97316",
  Midstream:      "#3b82f6",
  Downstream:     "#22c55e",
  Integrated:     "#8b5cf6",
  Petrochemicals: "#eab308",
  Services:       "#6b7280",
};
const DEFAULT_COLOR = "#94a3b8";

// $10K … $1T at major (×10) and minor (×2.5, ×5) intervals
const NICE_TICKS = [
  1e4, 2.5e4, 5e4,
  1e5, 2.5e5, 5e5,
  1e6, 2.5e6, 5e6,
  1e7, 2.5e7, 5e7,
  1e8, 2.5e8, 5e8,
  1e9, 2.5e9, 5e9,
  1e10, 2.5e10, 5e10,
  1e11, 2.5e11, 5e11,
  1e12,
];

// Tooltip formatter — strips trailing .0 but keeps meaningful decimals
function fmt(v: number): string {
  const c = (n: number) => +n.toFixed(2); // removes trailing zeros
  if (v >= 1e12) return `$${c(v / 1e12)}T`;
  if (v >= 1e9)  return `$${c(v / 1e9)}B`;
  if (v >= 1e6)  return `$${+(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3)  return `$${+(v / 1e3).toFixed(1)}K`;
  return `$${v.toLocaleString()}`;
}

// Axis tick formatter — same but handles the ×2.5 and ×5 values cleanly
function fmtTick(v: number): string {
  const clean = (n: number) => +n.toFixed(3); // strips float noise (2.5000000001 → 2.5)
  if (v >= 1e12) return `$${clean(v / 1e12)}T`;
  if (v >= 1e9)  return `$${clean(v / 1e9)}B`;
  if (v >= 1e6)  return `$${clean(v / 1e6)}M`;
  if (v >= 1e3)  return `$${clean(v / 1e3)}K`;
  return `$${v}`;
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
  id: number;
  name: string;
  ticker?: string;
  fy?: string;
  ps: number;
}

// Draws P/S = 1x and P/S = 3x reference diagonals behind the bubbles.
// On a log-log chart, y = k·x is a straight line, so two canvas points suffice.
const psReferenceLinePlugin: Plugin<"bubble"> = {
  id: "psReferenceLine",
  beforeDatasetsDraw(chart) {
    const xScale = chart.scales["x"];
    const yScale = chart.scales["y"];
    if (!xScale || !yScale) return;
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    const { left, right, top, bottom } = chartArea;

    ctx.save();
    // Clip so lines don't bleed into axis label margins
    ctx.beginPath();
    ctx.rect(left, top, right - left, bottom - top);
    ctx.clip();

    function drawLine(ps: number, color: string, label: string) {
      // Span well beyond any realistic data range; clipping handles visibility
      ctx.beginPath();
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.moveTo(xScale.getPixelForValue(1e4),  yScale.getPixelForValue(1e4 * ps));
      ctx.lineTo(xScale.getPixelForValue(1e13), yScale.getPixelForValue(1e13 * ps));
      ctx.stroke();

      // Label anchored to the right edge of the chart area at the line's y-position
      const xAtRight = xScale.getValueForPixel(right) ?? 1e12;
      const labelY = Math.max(top + 12, Math.min(bottom - 6,
        yScale.getPixelForValue(xAtRight * ps) - 5));
      ctx.setLineDash([]);
      ctx.font = "10px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = color;
      ctx.textAlign = "right";
      ctx.fillText(label, right - 6, labelY);
    }

    drawLine(1, "rgba(100,116,139,0.6)",  "P/S = 1x");
    drawLine(3, "rgba(100,116,139,0.35)", "P/S = 3x");

    ctx.restore();
  },
};

export default function Analytics() {
  const navigate = useNavigate();
  const [data, setData] = useState<{ total: number; included: number; items: ScatterPoint[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [posFilter, setPosFilter] = useState("all");
  const [psFilter, setPsFilter] = useState<PSFilter>("all");
  const [terrFilter, setTerrFilter] = useState("all");
  const [countryFilter, setCountryFilter] = useState("all");
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

  const countries = useMemo(() => {
    if (!data) return [];
    return Array.from(
      new Set(data.items.map(c => c.country).filter((c): c is string => !!c))
    ).sort();
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.items.filter(c => {
      if (terrFilter !== "all" && c.territory !== terrFilter) return false;
      if (countryFilter !== "all" && c.country !== countryFilter) return false;
      if (posFilter !== "all" && c.supply_chain_position !== posFilter) return false;
      const ps = c.market_cap_usd / c.revenue_annual_usd;
      if (psFilter === "under1" && ps >= 1) return false;
      if (psFilter === "1to3" && (ps < 1 || ps > 3)) return false;
      if (psFilter === "over3" && ps <= 3) return false;
      return true;
    });
  }, [data, terrFilter, countryFilter, posFilter, psFilter]);

  const metrics = useMemo(() => {
    const psRatios = filtered.map(c => c.market_cap_usd / c.revenue_annual_usd);
    return {
      count: filtered.length,
      medianPS: median(psRatios),
      under1: psRatios.filter(p => p < 1).length,
      over3: psRatios.filter(p => p > 3).length,
    };
  }, [filtered]);

  // Filtered by territory + country only — position is the grouping axis in chart 2
  const filteredForPos = useMemo(() => {
    if (!data) return [];
    return data.items.filter(c => {
      if (terrFilter !== "all" && c.territory !== terrFilter) return false;
      if (countryFilter !== "all" && c.country !== countryFilter) return false;
      return true;
    });
  }, [data, terrFilter, countryFilter]);

  const posGroups = useMemo(() => {
    const acc: Record<string, { cap: number; count: number }> = {};
    for (const c of filteredForPos) {
      const pos = c.supply_chain_position ?? "Other";
      if (!acc[pos]) acc[pos] = { cap: 0, count: 0 };
      acc[pos].cap += c.market_cap_usd;
      acc[pos].count += 1;
    }
    return Object.entries(acc)
      .sort((a, b) => b[1].cap - a[1].cap)
      .map(([pos, v]) => ({ pos, ...v }));
  }, [filteredForPos]);

  const posChartData = useMemo((): ChartData<"bar"> => ({
    labels: posGroups.map(g => g.pos),
    datasets: [{
      label: "Total Market Cap",
      data: posGroups.map(g => g.cap),
      backgroundColor: posGroups.map(g => (COLORS[g.pos] ?? DEFAULT_COLOR) + "bb"),
      borderColor: posGroups.map(g => COLORS[g.pos] ?? DEFAULT_COLOR),
      borderWidth: 1,
      borderRadius: 4,
    }],
  }), [posGroups]);

  const posOptions = useMemo((): ChartOptions<"bar"> => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items) => items[0]?.label ?? "",
          label: (ctx) => {
            const g = posGroups[ctx.dataIndex];
            return [
              `Market Cap: ${fmt(ctx.parsed.y ?? 0)}`,
              `Companies: ${g?.count ?? 0}`,
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
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: "#6b7280", font: { size: 12 } },
      },
      y: {
        title: { display: true, text: "Total Market Cap (USD)", font: { size: 12 }, color: "#6b7280" },
        ticks: { color: "#6b7280", callback: (v) => fmt(Number(v)) },
        grid: { color: "#f0f2f5" },
      },
    },
  }), [posGroups]);

  const chartData = useMemo((): ChartData<"bubble", BubbleDatum[]> => {
    const groups: Record<string, BubbleDatum[]> = {};
    for (const c of filtered) {
      const pos = c.supply_chain_position ?? "Other";
      if (!groups[pos]) groups[pos] = [];
      groups[pos].push({
        x: c.revenue_annual_usd,
        y: c.market_cap_usd,
        r: bubbleR(c.revenue_annual_usd),
        id: c.id,
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
    onClick(_event, elements, chart) {
      if (!elements.length) return;
      const { datasetIndex, index } = elements[0];
      const d = chart.data.datasets[datasetIndex]?.data[index] as BubbleDatum | undefined;
      if (!d) return;
      navigate(d.ticker ? `/company/${d.ticker}` : `/companies/${d.id}`);
    },
    onHover(_event, elements, chart) {
      chart.canvas.style.cursor = elements.length ? "pointer" : "default";
    },
    scales: {
      x: {
        type: "logarithmic",
        title: { display: true, text: "Annual Revenue (USD)", font: { size: 12 }, color: "#6b7280" },
        // Inject dense custom ticks (powers of 10 plus ×2.5 and ×5 intermediates)
        afterBuildTicks: (axis: any) => {
          axis.ticks = NICE_TICKS.map(v => ({ value: v }));
        },
        ticks: {
          color: "#6b7280",
          callback: (v: number | string) => fmtTick(Number(v)),
          font: { size: 9 },
          maxRotation: 45,
          minRotation: 45,
        },
        grid: { color: "#f0f2f5" },
      } as any,
      y: {
        type: "logarithmic",
        title: { display: true, text: "Market Cap (USD)", font: { size: 12 }, color: "#6b7280" },
        afterBuildTicks: (axis: any) => {
          axis.ticks = NICE_TICKS.map(v => ({ value: v }));
        },
        ticks: {
          color: "#6b7280",
          callback: (v: number | string) => fmtTick(Number(v)),
          font: { size: 9 },
        },
        grid: { color: "#f0f2f5" },
      } as any,
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
                  Bubble size = revenue. Dashed lines = P/S ratios of 1x and 3x. Coloured by energy value chain position.
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
                <select style={selectStyle} value={countryFilter} onChange={e => setCountryFilter(e.target.value)}>
                  <option value="all">All countries</option>
                  {countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select style={selectStyle} value={posFilter} onChange={e => setPosFilter(e.target.value)}>
                  <option value="all">All energy value chain positions</option>
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

            <hr style={{ margin: "32px 0", border: "none", borderTop: "1px solid #e0e4ea" }} />

            {/* ── Section: Market cap by supply chain position ── */}
            <div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e" }}>
                  Market cap by energy value chain position
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                  Total market cap of companies with financial data, grouped by position.
                  {terrFilter !== "all" && ` Filtered to ${terrFilter}.`}
                  {countryFilter !== "all" && ` Filtered to ${countryFilter}.`}
                </div>
              </div>

              <div className="card" style={{ padding: 24 }}>
                <div style={{ height: 300 }}>
                  {posGroups.length > 0 ? (
                    <Bar data={posChartData} options={posOptions} />
                  ) : (
                    <div style={{
                      display: "flex", alignItems: "center", justifyContent: "center",
                      height: "100%", color: "#9ca3af", fontSize: 14,
                    }}>
                      No data available.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
