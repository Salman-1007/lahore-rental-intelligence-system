"""Pydantic request/response schemas for listing and location endpoints."""

from pydantic import BaseModel, ConfigDict


class ListingOut(BaseModel):
    """A listing as returned by `/search` and `/listings/{id}`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: float
    size_marla: float | None = None
    property_type: str | None = None
    portion_type: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    location_name: str | None = None
    source: str
    source_url: str


class LocationOut(BaseModel):
    """A location as returned by `/autocomplete`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    level: str
