"""Stats service: aggregate market statistics for the `/stats` endpoint."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dimension import Dimension
from app.models.listing import Listing
from app.models.property_details import PropertyDetails
from app.schemas.stats import StatsResponse


def get_market_stats(session: Session) -> StatsResponse:
    """Compute aggregate stats across all listings.

    Args:
        session: Active DB session.

    Returns:
        Total/active counts, average price, average price-per-marla, and
        a breakdown of active listings by property type.
    """
    total = session.execute(select(func.count(Listing.id))).scalar_one()
    active = session.execute(
        select(func.count(Listing.id)).where(Listing.is_active.is_(True))
    ).scalar_one()

    avg_price = session.execute(
        select(func.avg(Listing.current_price)).where(Listing.is_active.is_(True))
    ).scalar_one()

    avg_price_per_marla = session.execute(
        select(func.avg(Listing.current_price / Dimension.size_marla))
        .join(Dimension, Dimension.listing_id == Listing.id)
        .where(Listing.is_active.is_(True))
    ).scalar_one()

    by_type_rows = session.execute(
        select(PropertyDetails.property_type, func.count(Listing.id))
        .join(Listing, Listing.id == PropertyDetails.listing_id)
        .where(Listing.is_active.is_(True))
        .group_by(PropertyDetails.property_type)
    ).all()
    listings_by_property_type = {ptype.value: count for ptype, count in by_type_rows}

    return StatsResponse(
        total_listings=total,
        active_listings=active,
        average_price=float(avg_price) if avg_price is not None else None,
        average_price_per_marla=(
            float(avg_price_per_marla) if avg_price_per_marla is not None else None
        ),
        listings_by_property_type=listings_by_property_type,
    )
