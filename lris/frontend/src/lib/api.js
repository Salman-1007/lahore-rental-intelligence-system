/**
 * Thin fetch wrapper around the LRIS FastAPI backend.
 *
 * In local development, requests go through Vite's dev-server proxy (see
 * vite.config.js), which forwards /api/* to http://127.0.0.1:8000 - so
 * BASE defaults to a relative path and this file never needs to know the
 * backend's actual host/port locally.
 *
 * In production (e.g. a static build deployed to Vercel/Netlify), there
 * is no dev proxy, so the built frontend needs to know the deployed
 * backend's real URL. Set VITE_API_BASE_URL at build time, e.g.:
 *   VITE_API_BASE_URL=https://your-backend.onrender.com/api/v1 npm run build
 * or configure it as an environment variable in your hosting dashboard.
 */

const BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || `Request failed: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export function searchListings(params) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return request(`/search?${query}`);
}

export function getListing(id) {
  return request(`/listings/${id}`);
}

export function autocompleteLocations(q) {
  if (!q || q.trim().length === 0) return Promise.resolve([]);
  return request(`/autocomplete?q=${encodeURIComponent(q)}&limit=8`);
}

export function predictRent(payload) {
  return request(`/predict`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getStats() {
  return request(`/stats`);
}

export function getTrends(locationId) {
  const query = locationId ? `?location_id=${locationId}` : "";
  return request(`/trends${query}`);
}
