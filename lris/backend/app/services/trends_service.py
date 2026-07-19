"""Trends service: monthly price aggregation for the `/trends` endpoint."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.models.price_history import PriceHistory
from app.schemas.stats import TrendPoint, TrendsResponse


def get_price_trends(session: Session, location_id: int | None = None) -> TrendsResponse:
    """Compute month-over-month average price and listing count.

    Args:
        session: Active DB session.
        location_id: If given, restricts to listings at that location.

    Returns:
        A `TrendsResponse` with one `TrendPoint` per calendar month that
        has at least one price observation.
    """
    # Month-truncation is expressed differently per SQL dialect (SQLite's
    # strftime vs PostgreSQL's to_char), so this branches on the active
    # session's dialect rather than hardcoding one — this app runs SQLite
    # in local dev and PostgreSQL (Neon) in production, and previously
    # this function only worked against SQLite, throwing a real SQL error
    # once deployed against Postgres.
    dialect_name = session.bind.dialect.name if session.bind is not None else "sqlite"

    if dialect_name == "postgresql":
        period_expr = func.to_char(PriceHistory.observed_at, "YYYY-MM")
    else:
        period_expr = func.strftime("%Y-%m", PriceHistory.observed_at)

    stmt = (
        select(period_expr.label("period"), func.avg(PriceHistory.price), func.count())
        .join(Listing, Listing.id == PriceHistory.listing_id)
        .group_by(period_expr)
        .order_by(period_expr)
    )
    if location_id is not None:
        stmt = stmt.where(Listing.location_id == location_id)

    rows = session.execute(stmt).all()
    points = [
        TrendPoint(period=period, average_price=float(avg_price), listing_count=count)
        for period, avg_price, count in rows
    ]

    return TrendsResponse(location_id=location_id, points=points)
