import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { formatPKR, titleCase } from "../components/ListingCard.jsx";
import { getListing } from "../lib/api.js";

export default function ListingPage() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    setStatus("loading");
    getListing(id)
      .then((res) => {
        setListing(res);
        setStatus("done");
      })
      .catch(() => setStatus("error"));
  }, [id]);

  if (status === "loading") {
    return (
      <div className="container">
        <p className="muted-note">Retrieving record…</p>
      </div>
    );
  }

  if (status === "error" || !listing) {
    return (
      <div className="container">
        <p className="muted-note error-note">This record could not be found.</p>
        <Link to="/" className="btn btn-ghost" style={{ marginTop: 16 }}>
          Back to Search
        </Link>
      </div>
    );
  }

  const facts = [
    ["Locality", listing.location_name || "Unresolved"],
    ["Property Type", titleCase(listing.property_type)],
    ["Portion Type", titleCase(listing.portion_type)],
    ["Size", listing.size_marla ? `${listing.size_marla} marla` : "—"],
    ["Bedrooms", listing.bedrooms ?? "—"],
    ["Bathrooms", listing.bathrooms ?? "—"],
    ["Source", titleCase(listing.source)],
  ];

  return (
    <div className="container listing-detail">
      <Link to="/" className="back-link">
        ← Back to Search
      </Link>

      <div className="card listing-detail-card">
        <span className="eyebrow">Listing Record #{listing.id}</span>
        <h1>{listing.title}</h1>
        <div className="listing-detail-price mono-figure">Rs {formatPKR(listing.price)} / month</div>

        <hr className="divider" />

        <dl className="fact-grid">
          {facts.map(([label, value]) => (
            <div className="fact" key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        <a
          href={listing.source_url}
          target="_blank"
          rel="noreferrer"
          className="btn btn-ghost"
          style={{ marginTop: 20 }}
        >
          View Original Listing ↗
        </a>
      </div>
    </div>
  );
}
