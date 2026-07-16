"""`/search` endpoint: filtered listing search."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingOut

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[ListingOut])
def search_listings(
    location_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_size_marla: float | None = None,
    max_size_marla: float | None = None,
    bedrooms: int | None = None,
    property_type: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    session: Session = Depends(get_db),
) -> list[ListingOut]:
    """Search active listings against common filters."""
    repo = ListingRepository(session)
    listings = repo.search(
        location_id=location_id,
        min_price=min_price,
        max_price=max_price,
        min_size_marla=min_size_marla,
        max_size_marla=max_size_marla,
        bedrooms=bedrooms,
        property_type=property_type,
        limit=limit,
        offset=offset,
    )
    return [_to_listing_out(listing) for listing in listings]


def _to_listing_out(listing) -> ListingOut:
    return ListingOut(
        id=listing.id,
        title=listing.title,
        price=listing.current_price,
        size_marla=listing.dimension.size_marla if listing.dimension else None,
        property_type=(
            listing.property_details.property_type.value if listing.property_details else None
        ),
        portion_type=(
            listing.property_details.portion_type.value if listing.property_details else None
        ),
        bedrooms=listing.property_details.bedrooms if listing.property_details else None,
        bathrooms=listing.property_details.bathrooms if listing.property_details else None,
        location_name=listing.location.name if listing.location else None,
        source=listing.source.name.value,
        source_url=listing.source_url,
    )
