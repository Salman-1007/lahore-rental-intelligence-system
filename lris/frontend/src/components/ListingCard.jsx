import { Link } from "react-router-dom";

function formatPKR(amount) {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-PK", { maximumFractionDigits: 0 }).format(amount);
}

function titleCase(text) {
  if (!text) return "—";
  return text.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ListingCard({ listing }) {
  return (
    <Link to={`/listings/${listing.id}`} className="listing-card card">
      <div className="listing-card-main">
        <h3 className="listing-card-title">{listing.title}</h3>
        <div className="listing-card-meta">
          <span>{listing.location_name || "Location unresolved"}</span>
          <span className="dot">·</span>
          <span>{titleCase(listing.property_type)}</span>
          {listing.size_marla && (
            <>
              <span className="dot">·</span>
              <span>{listing.size_marla} marla</span>
            </>
          )}
          {listing.bedrooms != null && (
            <>
              <span className="dot">·</span>
              <span>{listing.bedrooms} bed</span>
            </>
          )}
        </div>
      </div>
      <div className="listing-card-price">
        <span className="eyebrow">Monthly Rent</span>
        <span className="mono-figure listing-card-amount">Rs {formatPKR(listing.price)}</span>
        <span className="listing-card-source">{titleCase(listing.source)}</span>
      </div>
    </Link>
  );
}

export { formatPKR, titleCase };
