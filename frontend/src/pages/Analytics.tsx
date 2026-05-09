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
import { fetchScatterData, fetchChartsData } from "../api/client";
import type { ScatterPoint, ChartsData } from "../types";

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

const TERR_COLORS = [
  "#3b82f6", "#f97316", "#22c55e", "#8b5cf6",
  "#eab308", "#ef4444", "#06b6d4", "#ec4899",
  "#84cc16", "#f59e0b",
];

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

function fmt(v: number): string {
  const c = (n: number) => +n.toFixed(2);
  if (v >= 1e12) return `$${c(v / 1e12)}T`;
  if (v >= 1e9)  return `$${c(v / 1e9)}B`;
  if (v >= 1e6)  return `$${+(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3)  return `$${+(v / 1e3).toFixed(1)}K`;
  return `$${v.toLocaleString()}`;
}

function fmtTick(v: number): string {
  const clean = (n: number) => +n.toFixed(3);
  if (v >= 1e12) return `$${clean(v / 1e12)}T`;
  if (v >= 1e9)  return `$${clean(v / 1e9)}B`;
  if (v >= 1e6)  return `$${clean(v / 1e6)}M`;
  if (v >= 1e3)  return `$${clean(v / 1e3)}K`;
  return `$${v}`;
}

function bubbleR(revUsd: number): number {
  return Math.max(4, Math.min(20, Math.sqrt(revUsd / 1e9) * 1.8));
}

function capBubbleR(totalCap: number, maxCap: number): number {
  return Math.max(6, Math.min(40, Math.sqrt(totalCap / maxCap) * 36));
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

interface TerrBubbleDatum extends BubbleDataPoint {
  territory: string;
  company_count: number;
  total_cap: number;
}

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
    ctx.beginPath();
    ctx.rect(left, top, right - left, bottom - top);
    ctx.clip();

    function drawLine(ps: number, color: string, label: string) {
      ctx.beginPath();
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.moveTo(xScale.getPixelForValue(1e4),  yScale.getPixelForValue(1e4 * ps));
      ctx.lineTo(xScale.getPixelForValue(1e13), yScale.getPixelForValue(1e13 * ps));
      ctx.stroke();

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

// Plugin: median reference line on horizontal bar chart (Chart 2)
function makeMedianPlugin(getMedian: () => number): Plugin<"bar"> {
  return {
    id: "medianRefLine",
    afterDatasetsDraw(chart) {
      const xScale = chart.scales["x"];
      const { ctx, chartArea } = chart;
      if (!xScale || !chartArea) return;
      const m = getMedian();
      if (!m) return;
      const x = xScale.getPixelForValue(m);
      ctx.save();
      ctx.beginPath();
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = "rgba(100,116,139,0.7)";
      ctx.lineWidth = 1.5;
      ctx.moveTo(x, chartArea.top);
      ctx.lineTo(x, chartArea.bottom);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "10px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillStyle = "rgba(100,116,139,0.9)";
      ctx.textAlign = "center";
      ctx.fillText(`Median ${m.toFixed(1)}x`, x, chartArea.top - 4);
      ctx.restore();
    },
  };
}

// Plugin: bar-end labels for chart 2 (horizontal bars)
const barEndLabelPlugin: Plugin<"bar"> = {
  id: "barEndLabel",
  afterDatasetsDraw(chart) {
    const { ctx, chartArea } = chart;
    const dataset = chart.data.datasets[0];
    if (!dataset) return;
    const meta = chart.getDatasetMeta(0);
    ctx.save();
    ctx.font = "11px -apple-system, BlinkMacSystemFont, sans-serif";
    ctx.fillStyle = "#374151";
    meta.data.forEach((bar, i) => {
      const val = (dataset.data[i] as number) ?? 0;
      const extra = (dataset as any)._extraLabels?.[i] ?? "";
      const x = Math.min((bar as any).x + 4, chartArea.right - 2);
      ctx.textAlign = "left";
      ctx.fillText(`${val.toFixed(1)}x ${extra}`, x, bar.y + 4);
    });
    ctx.restore();
  },
};

// Plugin: territory name labels on bubble (Chart 4)
// Uses d.r (pixel radius set in chart4Data) because Chart.js el.options.radius
// is unreliable across render cycles; d.r is always the source of truth.
const terrLabelPlugin: Plugin<"bubble"> = {
  id: "terrLabel",
  afterDatasetsDraw(chart) {
    const { ctx, chartArea } = chart;
    if (!chartArea) return;
    chart.data.datasets.forEach((ds, di) => {
      const meta = chart.getDatasetMeta(di);
      meta.data.forEach((el, i) => {
        const d = ds.data[i] as TerrBubbleDatum;
        if (!d?.territory) return;
        const r = (d as any).r as number ?? 10;
        const labelY = el.y - r - 5;
        ctx.save();
        ctx.font = "bold 10px -apple-system, BlinkMacSystemFont, sans-serif";
        ctx.textAlign = "center";
        // White halo so text is readable over any bubble colour
        ctx.lineWidth = 3;
        ctx.strokeStyle = "rgba(255,255,255,0.85)";
        ctx.strokeText(d.territory, el.x, labelY);
        ctx.fillStyle = "#1e293b";
        ctx.fillText(d.territory, el.x, labelY);
        ctx.restore();
      });
    });
  },
};

export default function Analytics() {
  const navigate = useNavigate();
  const [data, setData] = useState<{ total: number; included: number; items: ScatterPoint[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [chartsData, setChartsData] = useState<ChartsData | null>(null);
  const [chartsLoading, setChartsLoading] = useState(false);
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

  // Fetch charts data whenever filters change
  useEffect(() => {
    setChartsLoading(true);
    const params = {
      territory: terrFilter !== "all" ? terrFilter : "",
      country: countryFilter !== "all" ? countryFilter : "",
      value_chain: posFilter !== "all" ? posFilter : "",
      ps_filter: psFilter !== "all" ? psFilter : "",
    };
    fetchChartsData(params)
      .then(d => setChartsData(d))
      .catch(() => null)
      .finally(() => setChartsLoading(false));
  }, [terrFilter, countryFilter, posFilter, psFilter]);

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
    const all = Array.from(
      new Set(data.items.map(c => c.country).filter((c): c is string => !!c))
    ).sort();
    const rest = all.filter(c => c !== "United States");
    return all.includes("United States") ? ["United States", ...rest] : rest;
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

  // ── Chart 2: Median P/S by segment (horizontal bar) ──
  const chart2Data = useMemo((): ChartData<"bar"> => {
    if (!chartsData) return { labels: [], datasets: [] };
    const sorted = [...chartsData.by_segment].sort((a, b) => b.median_ps - a.median_ps);
    const extraLabels = sorted.map(s => `(${s.company_count})`);
    const ds: any = {
      label: "Median P/S",
      data: sorted.map(s => s.median_ps),
      backgroundColor: sorted.map(s => (COLORS[s.segment] ?? DEFAULT_COLOR) + "bb"),
      borderColor: sorted.map(s => COLORS[s.segment] ?? DEFAULT_COLOR),
      borderWidth: 1,
      borderRadius: 4,
      _extraLabels: extraLabels,
    };
    return {
      labels: sorted.map(s => s.segment),
      datasets: [ds],
    };
  }, [chartsData]);

  const overallMedianPs = chartsData?.overall_median_ps ?? 0;
  const medianPlugin = useMemo(() => makeMedianPlugin(() => overallMedianPs), [overallMedianPs]);

  const chart2Options = useMemo((): ChartOptions<"bar"> => ({
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y" as const,
    layout: { padding: { right: 100 } },
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items) => items[0]?.label ?? "",
          label: (ctx) => {
            const seg = chartsData?.by_segment.find(s => s.segment === ctx.label);
            const overall = chartsData?.overall_median_ps ?? 0;
            const ps = ctx.parsed.x ?? 0;
            const diff = overall ? ((ps - overall) / overall * 100) : 0;
            const sign = diff >= 0 ? "↑" : "↓";
            return [
              `Median P/S: ${ps.toFixed(1)}x`,
              `Companies: ${seg?.company_count ?? 0}`,
              `${sign} ${Math.abs(diff).toFixed(0)}% vs overall median (${overall.toFixed(1)}x)`,
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
        title: { display: true, text: "Median P/S Ratio", color: "#6b7280", font: { size: 12 } },
        ticks: { color: "#6b7280", callback: (v) => `${Number(v).toFixed(1)}x` },
        grid: { color: "#f0f2f5" },
      },
      y: {
        grid: { display: false },
        ticks: { color: "#374151", font: { size: 12 } },
      },
    },
  }), [chartsData]);

  // ── Chart 3: Revenue share vs Market cap share (grouped bar) ──
  const chart3Data = useMemo((): ChartData<"bar"> => {
    if (!chartsData) return { labels: [], datasets: [] };
    // Already sorted by implied_ps desc from backend
    const segs = chartsData.by_segment;
    return {
      labels: segs.map(s => `${s.segment} — ${s.implied_ps.toFixed(1)}x`),
      datasets: [
        {
          label: "Revenue Share",
          data: segs.map(s => s.revenue_share * 100),
          backgroundColor: segs.map(s => (COLORS[s.segment] ?? DEFAULT_COLOR) + "cc"),
          borderColor: segs.map(s => COLORS[s.segment] ?? DEFAULT_COLOR),
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Market Cap Share",
          data: segs.map(s => s.cap_share * 100),
          backgroundColor: segs.map(s => (COLORS[s.segment] ?? DEFAULT_COLOR) + "55"),
          borderColor: segs.map(s => COLORS[s.segment] ?? DEFAULT_COLOR),
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    };
  }, [chartsData]);

  const chart3Options = useMemo((): ChartOptions<"bar"> => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: (items) => {
            const label = items[0]?.label ?? "";
            return label.split(" — ")[0];
          },
          label: (ctx) => {
            const segLabel = (ctx.label ?? "").split(" — ")[0];
            const seg = chartsData?.by_segment.find(s => s.segment === segLabel);
            if (!seg) return "";
            const isRev = ctx.datasetIndex === 0;
            const pct = (isRev ? seg.revenue_share : seg.cap_share) * 100;
            const label = isRev ? "Revenue share" : "Market cap share";
            const premium = seg.implied_ps > (chartsData?.overall_median_ps ?? 0);
            const indicator = isRev
              ? ""
              : ` ${premium ? "↑ premium" : "↓ discount"} (implied P/S ${seg.implied_ps.toFixed(1)}x)`;
            return `${label}: ${pct.toFixed(1)}%${indicator}`;
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
        ticks: { color: "#374151", font: { size: 11 }, maxRotation: 20 },
      },
      y: {
        title: { display: true, text: "Share of Total (%)", color: "#6b7280", font: { size: 12 } },
        ticks: { color: "#6b7280", callback: (v) => `${v}%` },
        grid: { color: "#f0f2f5" },
      },
    },
  }), [chartsData]);

  // ── Chart 4: Bubble — company count vs median market cap by territory ──
  const chart4Data = useMemo((): ChartData<"bubble", TerrBubbleDatum[]> => {
    if (!chartsData) return { datasets: [] };
    const maxCap = Math.max(...chartsData.by_territory.map(t => t.total_cap), 1);
    return {
      datasets: chartsData.by_territory.map((t, i) => ({
        label: t.territory,
        data: [{
          x: t.company_count,
          y: t.median_cap,
          r: capBubbleR(t.total_cap, maxCap),
          territory: t.territory,
          company_count: t.company_count,
          total_cap: t.total_cap,
        }],
        backgroundColor: (TERR_COLORS[i % TERR_COLORS.length]) + "99",
        borderColor: TERR_COLORS[i % TERR_COLORS.length],
        borderWidth: terrFilter !== "all" && t.territory === terrFilter ? 3 : 1,
      })),
    };
  }, [chartsData, terrFilter]);

  const chart4Options = useMemo((): ChartOptions<"bubble"> => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          title: () => "",
          label: (ctx) => {
            const d = ctx.raw as TerrBubbleDatum;
            return [
              d.territory,
              `Companies: ${d.company_count}`,
              `Median Market Cap: ${fmt(d.y as number)}`,
              `Total Market Cap: ${fmt(d.total_cap)}`,
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
        type: "logarithmic",
        title: { display: true, text: "Number of Companies", color: "#6b7280", font: { size: 12 } },
        afterBuildTicks: (axis: any) => {
          axis.ticks = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000].map(v => ({ value: v }));
        },
        ticks: {
          color: "#6b7280",
          callback: (v: number | string) => String(Number(v)),
        },
        grid: { color: "#f0f2f5" },
      } as any,
      y: {
        type: "logarithmic",
        title: { display: true, text: "Median Market Cap (USD)", color: "#6b7280", font: { size: 12 } },
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
  }), []);

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

  const anyFilterActive = terrFilter !== "all" || countryFilter !== "all" || posFilter !== "all" || psFilter !== "all";

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

              {/* Shared filter bar */}
              <div className="filter-bar" style={{ marginBottom: 16 }}>
                <select style={selectStyle} value={terrFilter} onChange={e => setTerrFilter(e.target.value)}>
                  <option value="all">All Territories</option>
                  {territories.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select style={selectStyle} value={countryFilter} onChange={e => setCountryFilter(e.target.value)}>
                  <option value="all">All Countries</option>
                  {countries.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select style={selectStyle} value={posFilter} onChange={e => setPosFilter(e.target.value)}>
                  <option value="all">All Energy Value Chain Positions</option>
                  {positions.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <select style={selectStyle} value={psFilter} onChange={e => setPsFilter(e.target.value as PSFilter)}>
                  <option value="all">All P/S Ratios</option>
                  <option value="under1">Under 1x</option>
                  <option value="1to3">1x – 3x</option>
                  <option value="over3">Over 3x</option>
                </select>
                {anyFilterActive && (
                  <button
                    onClick={() => { setTerrFilter("all"); setCountryFilter("all"); setPosFilter("all"); setPsFilter("all"); }}
                    style={{
                      padding: "7px 11px", border: "1px solid #d1d5db", borderRadius: 6,
                      fontSize: 13, background: "#fff", color: "#6b7280", cursor: "pointer",
                      display: "flex", alignItems: "center", gap: 5, whiteSpace: "nowrap",
                    }}
                  >
                    ↺ Reset
                  </button>
                )}
              </div>

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

            <hr style={{ margin: "32px 0", border: "none", borderTop: "1px solid #e0e4ea" }} />

            {/* ── Section: Median P/S by segment ── */}
            <div style={{ opacity: chartsLoading ? 0.4 : 1, transition: "opacity 0.2s" }}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e" }}>
                  Median P/S ratio by value chain position
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                  Sorted by median P/S descending. Dashed line = overall median across all filtered companies.
                </div>
              </div>

              <div className="card" style={{ padding: 24 }}>
                <div style={{ height: 320 }}>
                  {chartsData && chartsData.by_segment.length > 0 ? (
                    <Bar
                      data={chart2Data}
                      options={chart2Options}
                      plugins={[medianPlugin, barEndLabelPlugin]}
                    />
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

            <hr style={{ margin: "32px 0", border: "none", borderTop: "1px solid #e0e4ea" }} />

            {/* ── Section: Revenue share vs market cap share ── */}
            <div style={{ opacity: chartsLoading ? 0.4 : 1, transition: "opacity 0.2s" }}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e" }}>
                  Revenue share vs market cap share by segment
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                  Sorted by implied P/S (shown in axis labels). Solid = revenue share, faded = market cap share.
                  When market cap share exceeds revenue share, the segment commands a valuation premium.
                </div>
              </div>

              {/* Custom legend */}
              <div style={{ display: "flex", gap: 20, marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#374151" }}>
                  <span style={{ width: 14, height: 14, background: "#3b82f6cc", borderRadius: 2, display: "inline-block" }} />
                  Revenue share (solid)
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#374151" }}>
                  <span style={{ width: 14, height: 14, background: "#3b82f655", border: "1px solid #3b82f6", borderRadius: 2, display: "inline-block" }} />
                  Market cap share (faded)
                </div>
              </div>

              <div className="card" style={{ padding: 24 }}>
                <div style={{ height: 320 }}>
                  {chartsData && chartsData.by_segment.length > 0 ? (
                    <Bar data={chart3Data} options={chart3Options} />
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

            <hr style={{ margin: "32px 0", border: "none", borderTop: "1px solid #e0e4ea" }} />

            {/* ── Section: Territory bubble chart ── */}
            <div style={{ opacity: chartsLoading ? 0.4 : 1, transition: "opacity 0.2s" }}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: "#1a1a2e" }}>
                  Company count vs median market cap by territory
                </div>
                <div style={{ fontSize: 13, color: "#6b7280", marginTop: 2 }}>
                  Bubble size = total market cap. Y axis = median market cap per company (log scale).
                  {terrFilter !== "all" && ` Selected territory (${terrFilter}) shown with bold border.`}
                </div>
              </div>

              <div className="card" style={{ padding: 24 }}>
                <div style={{ height: 440 }}>
                  {chartsData && chartsData.by_territory.length > 0 ? (
                    <Bubble
                      data={chart4Data}
                      options={chart4Options}
                      plugins={[terrLabelPlugin]}
                    />
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
