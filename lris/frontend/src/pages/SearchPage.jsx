import { useEffect, useState } from "react";
import AutocompleteInput from "../components/AutocompleteInput.jsx";
import ListingCard from "../components/ListingCard.jsx";
import { searchListings } from "../lib/api.js";

const PROPERTY_TYPES = [
  { value: "", label: "Any type" },
  { value: "portion", label: "Portion" },
  { value: "upper_portion", label: "Upper Portion" },
  { value: "lower_portion", label: "Lower Portion" },
  { value: "house", label: "House" },
  { value: "flat", label: "Flat" },
  { value: "room", label: "Room" },
];

export default function SearchPage() {
  const [filters, setFilters] = useState({
    locationText: "",
    location_id: undefined,
    min_price: "",
    max_price: "",
    min_size_marla: "",
    max_size_marla: "",
    bedrooms: "",
  });
  const [listings, setListings] = useState([]);
  const [status, setStatus] = useState("idle");

  function runSearch(currentFilters) {
    setStatus("loading");
    searchListings({
      location_id: currentFilters.location_id,
      min_price: currentFilters.min_price,
      max_price: currentFilters.max_price,
      min_size_marla: currentFilters.min_size_marla,
      max_size_marla: currentFilters.max_size_marla,
      bedrooms: currentFilters.bedrooms,
      property_type: currentFilters.property_type,
    })
      .then((results) => {
        setListings(results);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }

  useEffect(() => {
    runSearch(filters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSubmit(e) {
    e.preventDefault();
    runSearch(filters);
  }

  return (
    <div className="container search-layout">
      <section className="hero jali-texture">
        <span className="eyebrow">Lahore · Rental Register</span>
        <h1>Search the record of listed rentals across Lahore</h1>
        <p className="hero-sub">
          Filter by property type, size, and locality to browse listings compiled
          from public sources and normalized into a single ledger.
        </p>
      </section>

      <div className="search-body">
        <aside className="filters card">
          <form onSubmit={handleSubmit}>
            <h3 className="filters-heading">Filter Records</h3>

            <div className="field">
              <label className="field-label">Locality</label>
              <AutocompleteInput
                value={filters.locationText}
                onChangeText={(text) =>
                  setFilters((f) => ({ ...f, locationText: text, location_id: undefined }))
                }
                onSelect={(loc) =>
                  setFilters((f) => ({ ...f, locationText: loc.name, location_id: loc.id }))
                }
              />
            </div>

            <div className="field">
              <label className="field-label">Property Type</label>
              <select
                className="input"
                value={filters.property_type || ""}
                onChange={(e) => setFilters((f) => ({ ...f, property_type: e.target.value }))}
              >
                {PROPERTY_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-row">
              <div className="field">
                <label className="field-label">Min Price (Rs)</label>
                <input
                  className="input"
                  type="number"
                  value={filters.min_price}
                  onChange={(e) => setFilters((f) => ({ ...f, min_price: e.target.value }))}
                />
              </div>
              <div className="field">
                <label className="field-label">Max Price (Rs)</label>
                <input
                  className="input"
                  type="number"
                  value={filters.max_price}
                  onChange={(e) => setFilters((f) => ({ ...f, max_price: e.target.value }))}
                />
              </div>
            </div>

            <div className="field-row">
              <div className="field">
                <label className="field-label">Min Size (marla)</label>
                <input
                  className="input"
                  type="number"
                  value={filters.min_size_marla}
                  onChange={(e) => setFilters((f) => ({ ...f, min_size_marla: e.target.value }))}
                />
              </div>
              <div className="field">
                <label className="field-label">Max Size (marla)</label>
                <input
                  className="input"
                  type="number"
                  value={filters.max_size_marla}
                  onChange={(e) => setFilters((f) => ({ ...f, max_size_marla: e.target.value }))}
                />
              </div>
            </div>

            <div className="field">
              <label className="field-label">Bedrooms</label>
              <input
                className="input"
                type="number"
                min="0"
                value={filters.bedrooms}
                onChange={(e) => setFilters((f) => ({ ...f, bedrooms: e.target.value }))}
              />
            </div>

            <button className="btn btn-primary" type="submit" style={{ width: "100%", marginTop: 8 }}>
              Apply Filters
            </button>
          </form>
        </aside>

        <section className="results">
          {status === "loading" && <p className="muted-note">Consulting the register…</p>}
          {status === "error" && (
            <p className="muted-note error-note">
              Couldn't reach the backend. Confirm the FastAPI server is running.
            </p>
          )}
          {status === "done" && listings.length === 0 && (
            <p className="muted-note">
              No records match these filters yet. Widen the search or scrape more data.
            </p>
          )}
          {listings.map((listing) => (
            <ListingCard key={listing.id} listing={listing} />
          ))}
        </section>
      </div>
    </div>
  );
}
