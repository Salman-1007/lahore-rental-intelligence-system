"""`/listings/{id}` endpoint: fetch a single listing with full details."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.search import _to_listing_out
from app.db.session import get_db
from app.repositories.listing_repository import ListingRepository
from app.schemas.listing import ListingOut

router = APIRouter(tags=["listings"])


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, session: Session = Depends(get_db)) -> ListingOut:
    """Fetch a single listing by ID, with dimension/details/location eager-loaded."""
    repo = ListingRepository(session)
    listing = repo.get_with_details(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _to_listing_out(listing)
