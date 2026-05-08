import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { fetchCompanies, fetchFilterOptions } from "../api/client";
import type { Company, FilterOptions, EnergySegment, ValueChainPosition } from "../types";
import { formatCap, formatPrice } from "../components/FormatCap";
import SupplyChainChart from "../components/SupplyChainChart";

const PAGE_SIZE = 50;

export default function CompanyList() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);

  // Filter state
  const [search, setSearch] = useState("");
  const [territory, setTerritory] = useState("");
  const [segment, setSegment] = useState("");
  const [chainPos, setChainPos] = useState("");
  const [supplyChain, setSupplyChain] = useState("");
  const [country, setCountry] = useState("");

  useEffect(() => {
    fetchFilterOptions().then(setFilters).catch(() => null);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchCompanies({
      search: search || undefined,
      wwt_territory: territory || undefined,
      energy_segment: (segment as EnergySegment) || undefined,
      value_chain_position: (chainPos as ValueChainPosition) || undefined,
      supply_chain_position: supplyChain || undefined,
      country: country || undefined,
      page,
      page_size: PAGE_SIZE,
    })
      .then((data) => {
        setCompanies(data.items);
        setTotal(data.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search, territory, segment, chainPos, supplyChain, country, page]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function handleFilterChange(setter: (v: string) => void) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setter(e.target.value);
      setPage(1);
    };
  }

  return (
    <>
      <div className="page-header">
        <h1>Companies</h1>
        <span style={{ color: "#6b7280", fontSize: 13 }}>{total.toLocaleString()} companies</span>
      </div>
      <div className="page-body">
        <SupplyChainChart />
        <div className="filter-bar">
          <input
            type="search"
            placeholder="Search company name..."
            value={search}
            onChange={handleFilterChange(setSearch)}
          />
          <select value={territory} onChange={handleFilterChange(setTerritory)}>
            <option value="">All territories</option>
            {filters?.wwt_territories.map((t) => <option key={t}>{t}</option>)}
          </select>
          <select value={segment} onChange={handleFilterChange(setSegment)}>
            <option value="">All segments</option>
            {filters?.energy_segments.map((s) => <option key={s}>{s}</option>)}
          </select>
          <select value={chainPos} onChange={handleFilterChange(setChainPos)}>
            <option value="">All value chain positions</option>
            {filters?.value_chain_positions.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select value={supplyChain} onChange={handleFilterChange(setSupplyChain)}>
            <option value="">All supply chain positions</option>
            {filters?.supply_chain_positions.map((v) => <option key={v}>{v}</option>)}
          </select>
          <select value={country} onChange={handleFilterChange(setCountry)}>
            <option value="">All countries</option>
            {filters?.countries.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            {loading ? (
              <div className="loading">Loading...</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Ticker</th>
                    <th>Territory</th>
                    <th>Segment</th>
                    <th>Supply Chain</th>
                    <th>Country</th>
                    <th style={{ textAlign: "right" }}>Market Cap</th>
                    <th style={{ textAlign: "right" }}>Price</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.length === 0 ? (
                    <tr><td colSpan={8} style={{ textAlign: "center", padding: "32px", color: "#9ca3af" }}>No companies match the current filters.</td></tr>
                  ) : companies.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <Link to={c.ticker ? `/company/${c.ticker}` : `/companies/${c.id}`} style={{ fontWeight: 500 }}>{c.name}</Link>
                      </td>
                      <td style={{ fontFamily: "monospace", color: "#6b7280" }}>{c.ticker ?? "—"}</td>
                      <td>{c.wwt_territory ? <span className="badge badge-territory">{c.wwt_territory}</span> : "—"}</td>
                      <td>{c.energy_segment ? <span className="badge badge-segment">{c.energy_segment}</span> : "—"}</td>
                      <td>{c.supply_chain_position ? <span className="badge badge-supply-chain">{c.supply_chain_position}</span> : "—"}</td>
                      <td>{c.country ?? "—"}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatCap(c.latest_market_cap)}</td>
                      <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{formatPrice(c.latest_price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <button onClick={() => setPage(1)} disabled={page === 1}>«</button>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>‹</button>
            <span>Page {page} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>›</button>
            <button onClick={() => setPage(totalPages)} disabled={page === totalPages}>»</button>
          </div>
        )}
      </div>
    </>
  );
}
