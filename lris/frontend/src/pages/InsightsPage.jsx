import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPKR, titleCase } from "../components/ListingCard.jsx";
import { getStats, getTrends } from "../lib/api.js";

function StatTile({ label, value, sub }) {
  return (
    <div className="stat-tile card">
      <span className="eyebrow">{label}</span>
      <div className="stat-tile-value mono-figure">{value}</div>
      {sub && <span className="stat-tile-sub">{sub}</span>}
    </div>
  );
}

export default function InsightsPage() {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    Promise.all([getStats(), getTrends()])
      .then(([statsRes, trendsRes]) => {
        setStats(statsRes);
        setTrends(trendsRes);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div className="container insights-layout">
      <section className="hero jali-texture">
        <span className="eyebrow">Market Insights</span>
        <h1>The state of the ledger</h1>
        <p className="hero-sub">
          Aggregate figures compiled across every active record, updated as new
          listings are scraped and normalized into the database.
        </p>
      </section>

      {status === "error" && (
        <p className="muted-note error-note">
          Couldn't reach the backend. Confirm the FastAPI server is running.
        </p>
      )}

      {status === "done" && stats && (
        <>
          <div className="stat-grid">
            <StatTile label="Total Records" value={stats.total_listings} />
            <StatTile label="Active Listings" value={stats.active_listings} />
            <StatTile
              label="Average Rent"
              value={stats.average_price ? `Rs ${formatPKR(stats.average_price)}` : "—"}
            />
            <StatTile
              label="Average Rate"
              value={
                stats.average_price_per_marla
                  ? `Rs ${formatPKR(stats.average_price_per_marla)}`
                  : "—"
              }
              sub="per marla"
            />
          </div>

          <div className="insights-grid">
            <div className="card trend-card">
              <h3 className="filters-heading">Average Price Over Time</h3>
              {trends && trends.points.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={trends.points}>
                    <defs>
                      <linearGradient id="brassFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#b98d4b" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#b98d4b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(185,141,75,0.1)" vertical={false} />
                    <XAxis
                      dataKey="period"
                      stroke="#6b746e"
                      tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }}
                    />
                    <YAxis
                      stroke="#6b746e"
                      tick={{ fontFamily: "IBM Plex Mono", fontSize: 11 }}
                      tickFormatter={(v) => `${Math.round(v / 1000)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#1b2124",
                        border: "1px solid rgba(185,141,75,0.32)",
                        borderRadius: 4,
                        fontFamily: "Inter",
                        fontSize: 12,
                      }}
                      formatter={(value) => [`Rs ${formatPKR(value)}`, "Average Price"]}
                    />
                    <Area
                      type="monotone"
                      dataKey="average_price"
                      stroke="#d7ad6c"
                      strokeWidth={2}
                      fill="url(#brassFill)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <p className="muted-note">Not enough price history yet to chart a trend.</p>
              )}
            </div>

            <div className="card breakdown-card">
              <h3 className="filters-heading">Active Listings by Property Type</h3>
              <ul className="breakdown-list">
                {Object.entries(stats.listings_by_property_type).map(([type, count]) => (
                  <li key={type}>
                    <span>{titleCase(type)}</span>
                    <span className="mono-figure">{count}</span>
                  </li>
                ))}
                {Object.keys(stats.listings_by_property_type).length === 0 && (
                  <p className="muted-note">No breakdown available yet.</p>
                )}
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
