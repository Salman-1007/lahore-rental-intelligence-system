"""`/trends` endpoint: month-over-month price trend, optionally by location."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import TrendsResponse
from app.services.trends_service import get_price_trends

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=TrendsResponse)
def read_trends(
    location_id: int | None = None, session: Session = Depends(get_db)
) -> TrendsResponse:
    """Return average price and listing count per calendar month."""
    return get_price_trends(session, location_id=location_id)
