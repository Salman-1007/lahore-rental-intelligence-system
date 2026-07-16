"""`/predict` endpoint: rent estimation for a described property."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.search import _to_listing_out
from app.db.session import get_db
from app.repositories.listing_repository import ListingRepository
from app.repositories.location_repository import LocationRepository
from app.schemas.predict import PredictRequest, PredictResponse
from app.services.prediction_service import (
    NoTrainedModelError,
    PredictionInput,
    PredictionService,
    get_prediction_service,
)

router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictResponse)
def predict_rent(
    request: PredictRequest,
    session: Session = Depends(get_db),
    service: PredictionService = Depends(get_prediction_service),
) -> PredictResponse:
    """Estimate rent for a property, including combinations never seen exactly in training."""
    location_id = request.location_id
    if location_id is None and request.location_name:
        location_repo = LocationRepository(session)
        matches = location_repo.fuzzy_search(request.location_name, limit=1)
        location_id = matches[0].id if matches else None

    prediction_input = PredictionInput(
        property_type=request.property_type,
        portion_type=request.portion_type,
        size_marla=request.size_marla,
        location_id=location_id,
        bedrooms=request.bedrooms,
        bathrooms=request.bathrooms,
        parking_spaces=request.parking_spaces,
        is_furnished=request.is_furnished,
        is_corner=request.is_corner,
        is_park_facing=request.is_park_facing,
        has_servant_quarter=request.has_servant_quarter,
        has_independent_entrance=request.has_independent_entrance,
        is_newly_built=request.is_newly_built,
    )

    try:
        result = service.predict(prediction_input, session)
    except NoTrainedModelError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    listing_repo = ListingRepository(session)
    similar_listings = [
        _to_listing_out(listing_repo.get_with_details(listing_id))
        for listing_id in result.similar_listing_ids
    ]

    return PredictResponse(
        estimated_price=result.estimated_price,
        confidence=result.confidence,
        minimum=result.minimum,
        maximum=result.maximum,
        model_version=result.model_version,
        similar_listings=similar_listings,
    )
