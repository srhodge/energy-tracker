import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { fetchSupplyChainRollup } from "../api/client";
import type { SupplyChainRollup } from "../types";

const COLORS: Record<string, string> = {
  Upstream:        "#f97316",
  Midstream:       "#3b82f6",
  Downstream:      "#22c55e",
  Integrated:      "#8b5cf6",
  Petrochemicals:  "#eab308",
  Services:        "#6b7280",
};

function fmt(v: number): string {
  if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toLocaleString()}`;
}

interface TooltipProps {
  active?: boolean;
  payload?: { value: number; payload: SupplyChainRollup }[];
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: "#fff", border: "1px solid #e0e4ea",
      borderRadius: 6, padding: "8px 12px", fontSize: 12,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.supply_chain_position}</div>
      <div>{fmt(d.total_market_cap_usd ?? 0)} market cap</div>
      <div style={{ color: "#6b7280" }}>{d.company_count} companies</div>
    </div>
  );
}

export default function SupplyChainChart() {
  const [data, setData] = useState<SupplyChainRollup[]>([]);

  useEffect(() => {
    fetchSupplyChainRollup()
      .then(rows => setData(rows.filter(r => r.total_market_cap_usd)))
      .catch(() => null);
  }, []);

  if (!data.length) return null;

  return (
    <div className="card" style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 12 }}>
        Market Cap by Supply Chain Position
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 24, top: 0, bottom: 0 }}>
          <XAxis
            type="number"
            tickFormatter={fmt}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="supply_chain_position"
            width={110}
            tick={{ fontSize: 12, fill: "#374151" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
          <Bar dataKey="total_market_cap_usd" radius={[0, 4, 4, 0]}>
            {data.map(entry => (
              <Cell
                key={entry.supply_chain_position}
                fill={COLORS[entry.supply_chain_position] ?? "#94a3b8"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
