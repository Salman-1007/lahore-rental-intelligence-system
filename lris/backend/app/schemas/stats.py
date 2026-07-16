"""Pydantic response schemas for `/stats` and `/trends`."""

from pydantic import BaseModel


class StatsResponse(BaseModel):
    """Aggregate market statistics."""

    total_listings: int
    active_listings: int
    average_price: float | None
    average_price_per_marla: float | None
    listings_by_property_type: dict[str, int]


class TrendPoint(BaseModel):
    """One point in a price trend time series."""

    period: str
    average_price: float
    listing_count: int


class TrendsResponse(BaseModel):
    """Price trend over time, optionally scoped to a location."""

    location_id: int | None
    points: list[TrendPoint]
