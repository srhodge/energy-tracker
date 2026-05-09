import { BrowserRouter, Routes, Route, NavLink, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import CompanyList from "./pages/CompanyList";
import CompanyDetail from "./pages/CompanyDetail";
import TerritoryDashboard from "./pages/TerritoryDashboard";
import ActivityFeed from "./pages/ActivityFeed";
import MissingData from "./pages/MissingData";
import Analytics from "./pages/Analytics";
import { fetchMissingData } from "./api/client";

function AppLayout() {
  const location = useLocation();
  const [missingCount, setMissingCount] = useState<number | null>(null);

  useEffect(() => {
    fetchMissingData()
      .then(d => {
        const ids = new Set([
          ...d.missing_website.map(c => c.id),
          ...d.missing_industry.map(c => c.id),
          ...d.missing_revenue.map(c => c.id),
        ]);
        setMissingCount(ids.size);
      })
      .catch(() => setMissingCount(null));
  }, [location.pathname]);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">Energy<span>Tracker</span></div>
        <nav className="sidebar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>Companies</NavLink>
          <NavLink to="/territories" className={({ isActive }) => isActive ? "active" : ""}>Territory Dashboard</NavLink>
          <NavLink to="/activity" className={({ isActive }) => isActive ? "active" : ""}>Activity Feed</NavLink>
          <NavLink to="/analytics" className={({ isActive }) => isActive ? "active" : ""}>Analytics</NavLink>
          {missingCount !== null && missingCount > 0 && (
            <NavLink
              to="/admin/missing-data"
              className={({ isActive }) => `nav-missing${isActive ? " active" : ""}`}
            >
              Missing Data <span className="nav-missing-badge">{missingCount}</span>
            </NavLink>
          )}
        </nav>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<CompanyList />} />
          <Route path="/companies/:id" element={<CompanyDetail />} />
          <Route path="/company/:ticker" element={<CompanyDetail />} />
          <Route path="/territories" element={<TerritoryDashboard />} />
          <Route path="/territories/:name" element={<TerritoryDashboard />} />
          <Route path="/activity" element={<ActivityFeed />} />
          <Route path="/admin/missing-data" element={<MissingData />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
