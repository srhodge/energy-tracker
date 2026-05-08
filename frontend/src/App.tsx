import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import CompanyList from "./pages/CompanyList";
import CompanyDetail from "./pages/CompanyDetail";
import TerritoryDashboard from "./pages/TerritoryDashboard";
import ActivityFeed from "./pages/ActivityFeed";

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-logo">Energy<span>Tracker</span></div>
          <nav className="sidebar-nav">
            <NavLink to="/" end className={({ isActive }) => isActive ? "active" : ""}>Companies</NavLink>
            <NavLink to="/territories" className={({ isActive }) => isActive ? "active" : ""}>Territory Dashboard</NavLink>
            <NavLink to="/activity" className={({ isActive }) => isActive ? "active" : ""}>Activity Feed</NavLink>
          </nav>
        </aside>
        <main className="main">
          <Routes>
            <Route path="/" element={<CompanyList />} />
            <Route path="/companies/:id" element={<CompanyDetail />} />
            <Route path="/company/:ticker" element={<CompanyDetail />} />
            <Route path="/territories" element={<TerritoryDashboard />} />
            <Route path="/activity" element={<ActivityFeed />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
