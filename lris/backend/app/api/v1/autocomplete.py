"""`/autocomplete` endpoint: fuzzy location search for the search UI."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.location_repository import LocationRepository
from app.schemas.listing import LocationOut

router = APIRouter(tags=["autocomplete"])


@router.get("/autocomplete", response_model=list[LocationOut])
def autocomplete_locations(
    q: str = Query(min_length=1),
    limit: int = Query(default=10, le=25),
    session: Session = Depends(get_db),
) -> list[LocationOut]:
    """Fuzzy-match a free-text query against the location hierarchy."""
    repo = LocationRepository(session)
    matches = repo.fuzzy_search(q, limit=limit)
    return [LocationOut.model_validate(loc) for loc in matches]
