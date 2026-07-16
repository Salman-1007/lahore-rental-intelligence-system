"""`/stats` endpoint: aggregate market statistics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import StatsResponse
from app.services.stats_service import get_market_stats

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def read_stats(session: Session = Depends(get_db)) -> StatsResponse:
    """Return aggregate counts, average price, and property-type breakdown."""
    return get_market_stats(session)
