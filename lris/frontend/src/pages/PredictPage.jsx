import { useState } from "react";
import AutocompleteInput from "../components/AutocompleteInput.jsx";
import EstimateCard from "../components/EstimateCard.jsx";
import { predictRent } from "../lib/api.js";

const PROPERTY_TYPES = [
  { value: "portion", label: "Portion" },
  { value: "upper_portion", label: "Upper Portion" },
  { value: "lower_portion", label: "Lower Portion" },
  { value: "house", label: "House" },
  { value: "flat", label: "Flat" },
  { value: "room", label: "Room" },
];

const PORTION_TYPES = [
  { value: "not_applicable", label: "Not applicable" },
  { value: "full_house", label: "Full House" },
  { value: "upper_portion", label: "Upper Portion" },
  { value: "lower_portion", label: "Lower Portion" },
  { value: "one_room", label: "One Room" },
];

const BOOLEAN_TOGGLES = [
  { key: "is_furnished", label: "Furnished" },
  { key: "is_corner", label: "Corner Plot" },
  { key: "is_park_facing", label: "Park Facing" },
  { key: "has_servant_quarter", label: "Servant Quarter" },
  { key: "has_independent_entrance", label: "Independent Entrance" },
  { key: "is_newly_built", label: "Newly Built" },
];

export default function PredictPage() {
  const [form, setForm] = useState({
    property_type: "portion",
    portion_type: "upper_portion",
    size_marla: 5,
    location_name: "",
    bedrooms: 2,
    bathrooms: 1,
    parking_spaces: 1,
    is_furnished: false,
    is_corner: false,
    is_park_facing: false,
    has_servant_quarter: false,
    has_independent_entrance: false,
    is_newly_built: false,
  });
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState("idle");
  const [errorMessage, setErrorMessage] = useState("");

  function toggle(key) {
    setForm((f) => ({ ...f, [key]: !f[key] }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setStatus("loading");
    setErrorMessage("");
    predictRent(form)
      .then((res) => {
        setResult(res);
        setStatus("done");
      })
      .catch((err) => {
        setStatus("error");
        setErrorMessage(err.message || "Unable to produce an estimate.");
      });
  }

  return (
    <div className="container predict-layout">
      <section className="hero jali-texture">
        <span className="eyebrow">Rent Estimation</span>
        <h1>Estimate rent for any combination — seen before or not</h1>
        <p className="hero-sub">
          The model reasons from learned relationships between size, locality, and
          property type, so it can estimate a combination — such as a 5 marla portion
          in a locality where only 3 and 10 marla have been recorded — without an
          exact match on file.
        </p>
      </section>

      <div className="predict-body">
        <form className="predict-form card" onSubmit={handleSubmit}>
          <h3 className="filters-heading">Describe the Property</h3>

          <div className="field-row">
            <div className="field">
              <label className="field-label">Property Type</label>
              <select
                className="input"
                value={form.property_type}
                onChange={(e) => setForm((f) => ({ ...f, property_type: e.target.value }))}
              >
                {PROPERTY_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label className="field-label">Portion Type</label>
              <select
                className="input"
                value={form.portion_type}
                onChange={(e) => setForm((f) => ({ ...f, portion_type: e.target.value }))}
              >
                {PORTION_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field">
            <label className="field-label">Locality</label>
            <AutocompleteInput
              value={form.location_name}
              onChangeText={(text) => setForm((f) => ({ ...f, location_name: text }))}
              onSelect={(loc) =>
                setForm((f) => ({ ...f, location_name: loc.name, location_id: loc.id }))
              }
            />
          </div>

          <div className="field-row">
            <div className="field">
              <label className="field-label">Size (marla)</label>
              <input
                className="input"
                type="number"
                step="0.5"
                min="0.5"
                value={form.size_marla}
                onChange={(e) => setForm((f) => ({ ...f, size_marla: Number(e.target.value) }))}
                required
              />
            </div>
            <div className="field">
              <label className="field-label">Bedrooms</label>
              <input
                className="input"
                type="number"
                min="0"
                value={form.bedrooms}
                onChange={(e) => setForm((f) => ({ ...f, bedrooms: Number(e.target.value) }))}
              />
            </div>
            <div className="field">
              <label className="field-label">Bathrooms</label>
              <input
                className="input"
                type="number"
                min="0"
                value={form.bathrooms}
                onChange={(e) => setForm((f) => ({ ...f, bathrooms: Number(e.target.value) }))}
              />
            </div>
          </div>

          <div className="field">
            <label className="field-label">Parking Spaces</label>
            <input
              className="input"
              type="number"
              min="0"
              value={form.parking_spaces}
              onChange={(e) => setForm((f) => ({ ...f, parking_spaces: Number(e.target.value) }))}
            />
          </div>

          <div className="field">
            <label className="field-label">Features</label>
            <div className="toggle-grid">
              {BOOLEAN_TOGGLES.map((toggleField) => (
                <label className="toggle-chip" key={toggleField.key}>
                  <input
                    type="checkbox"
                    checked={form[toggleField.key]}
                    onChange={() => toggle(toggleField.key)}
                  />
                  {toggleField.label}
                </label>
              ))}
            </div>
          </div>

          <button className="btn btn-primary" type="submit" style={{ width: "100%", marginTop: 12 }}>
            {status === "loading" ? "Estimating…" : "Produce Estimate"}
          </button>

          {status === "error" && <p className="muted-note error-note">{errorMessage}</p>}
        </form>

        <div className="predict-result">
          {result ? (
            <EstimateCard result={result} />
          ) : (
            <div className="card estimate-placeholder">
              <span className="eyebrow">Awaiting Entry</span>
              <p>
                Fill in the property details and submit to see the estimated monthly
                rent, its confidence, and a plausible range drawn from the model.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
