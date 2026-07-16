"""Pydantic request/response schemas for `/predict`."""

from pydantic import BaseModel, Field

from app.schemas.listing import ListingOut


class PredictRequest(BaseModel):
    """Attributes describing the (possibly unseen) property to estimate rent for."""

    property_type: str = Field(examples=["portion"])
    portion_type: str = Field(default="not_applicable")
    size_marla: float = Field(gt=0)
    location_id: int | None = None
    location_name: str | None = Field(
        default=None, description="Used to resolve `location_id` if it isn't provided directly."
    )
    bedrooms: int = 0
    bathrooms: int = 0
    parking_spaces: int = 0
    is_furnished: bool = False
    is_corner: bool = False
    is_park_facing: bool = False
    has_servant_quarter: bool = False
    has_independent_entrance: bool = False
    is_newly_built: bool = False


class PredictResponse(BaseModel):
    """Estimated rent, confidence, range, and comparable real listings."""

    estimated_price: float
    confidence: float
    minimum: float
    maximum: float
    model_version: str
    similar_listings: list[ListingOut]
