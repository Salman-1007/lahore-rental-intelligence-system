import { formatPKR } from "./ListingCard.jsx";
import ListingCard from "./ListingCard.jsx";

function confidenceLabel(score) {
  if (score >= 0.75) return "High";
  if (score >= 0.5) return "Moderate";
  return "Provisional";
}

export default function EstimateCard({ result }) {
  const rangeWidth = result.maximum - result.minimum || 1;
  const markerPosition = Math.min(
    100,
    Math.max(0, ((result.estimated_price - result.minimum) / rangeWidth) * 100)
  );

  return (
    <div className="estimate-card card">
      <div className="estimate-seal">
        <span className="eyebrow">Estimated Rent</span>
        <div className="estimate-amount mono-figure">Rs {formatPKR(result.estimated_price)}</div>
        <div className="estimate-confidence">
          <span className={`confidence-dot confidence-${confidenceLabel(result.confidence).toLowerCase()}`} />
          {confidenceLabel(result.confidence)} confidence ({Math.round(result.confidence * 100)}%)
        </div>
      </div>

      <div className="estimate-range">
        <div className="range-track">
          <div className="range-fill" style={{ left: 0, width: `${markerPosition}%` }} />
          <div className="range-marker" style={{ left: `${markerPosition}%` }} />
        </div>
        <div className="range-labels">
          <span className="mono-figure">Rs {formatPKR(result.minimum)}</span>
          <span className="mono-figure">Rs {formatPKR(result.maximum)}</span>
        </div>
      </div>

      {result.similar_listings && result.similar_listings.length > 0 && (
        <>
          <hr className="divider" />
          <h4 className="similar-heading">Comparable listings on record</h4>
          <div className="similar-list">
            {result.similar_listings.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
