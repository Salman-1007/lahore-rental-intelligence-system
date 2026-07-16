import { NavLink, Route, Routes } from "react-router-dom";
import SearchPage from "./pages/SearchPage.jsx";
import PredictPage from "./pages/PredictPage.jsx";
import InsightsPage from "./pages/InsightsPage.jsx";
import ListingPage from "./pages/ListingPage.jsx";

function Header() {
  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/" className="wordmark">
          <span className="wordmark-seal">L</span>
          <span className="wordmark-text">
            Lahore Rental Intelligence
            <small>Estate Records &amp; Estimation</small>
          </span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Search Records
          </NavLink>
          <NavLink to="/estimate" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Estimate Rent
          </NavLink>
          <NavLink to="/insights" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Market Insights
          </NavLink>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <Header />
      <main className="main">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/estimate" element={<PredictPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/listings/:id" element={<ListingPage />} />
        </Routes>
      </main>
      <footer className="footer">
        Lahore Rental Intelligence System — data compiled from public listing sources.
      </footer>
    </div>
  );
}
