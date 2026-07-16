"""Prediction service: loads the latest trained model artifacts and turns
a structured request into an estimate, confidence, range, and similar
listings.

This is the runtime counterpart to `ml/training/train.py` - it must build
feature vectors the exact same way training did (same column order, same
categorical encoding, same location-encoding lookup), or predictions will
silently be wrong.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from catboost import CatBoostRegressor
from sqlalchemy.orm import Session

from app.repositories.listing_repository import ListingRepository
from ml.features.feature_engineering import CATEGORICAL_FEATURES, FEATURE_COLUMNS
from ml.training.train import get_latest_model_dir

logger = logging.getLogger(__name__)


class NoTrainedModelError(Exception):
    """Raised when a prediction is requested but no model has been trained yet."""


@dataclass
class PredictionInput:
    """Structured attributes for a rent estimate request."""

    property_type: str
    portion_type: str
    size_marla: float
    location_id: int | None
    bedrooms: int = 0
    bathrooms: int = 0
    parking_spaces: int = 0
    is_furnished: bool = False
    is_corner: bool = False
    is_park_facing: bool = False
    has_servant_quarter: bool = False
    has_independent_entrance: bool = False
    is_newly_built: bool = False


@dataclass
class PredictionResult:
    """What the `/predict` endpoint returns."""

    estimated_price: float
    minimum: float
    maximum: float
    confidence: float
    model_version: str
    similar_listing_ids: list[int]


class PredictionService:
    """Loads a trained model bundle once and serves predictions from it."""

    def __init__(
        self,
        models_root: Path = Path("ml/models_registry"),
        data_root: Path = Path("data"),
    ) -> None:
        self.models_root = models_root
        self.data_root = data_root
        self._model_dir: Path | None = None
        self._main_model: CatBoostRegressor | None = None
        self._lower_model: CatBoostRegressor | None = None
        self._upper_model: CatBoostRegressor | None = None
        self._location_encoding: dict[str, float] | None = None
        self._metadata: dict | None = None

    def _ensure_loaded(self) -> None:
        latest_dir = get_latest_model_dir(self.models_root)
        if latest_dir is None:
            raise NoTrainedModelError(
                "No trained model found. Run `python -m ml.training.train <dataset_version>` first."
            )
        if self._model_dir == latest_dir:
            return

        logger.info("Loading model artifacts from %s", latest_dir)
        self._metadata = json.loads((latest_dir / "metadata.json").read_text())

        self._main_model = CatBoostRegressor()
        self._main_model.load_model(str(latest_dir / "main_model.cbm"))
        self._lower_model = CatBoostRegressor()
        self._lower_model.load_model(str(latest_dir / "lower_model.cbm"))
        self._upper_model = CatBoostRegressor()
        self._upper_model.load_model(str(latest_dir / "upper_model.cbm"))

        dataset_version = self._metadata["dataset_version"]
        encoding_path = self.data_root / "processed" / dataset_version / "location_encoding.json"
        self._location_encoding = json.loads(encoding_path.read_text())

        self._model_dir = latest_dir

    def _build_feature_row(self, request: PredictionInput) -> pd.DataFrame:
        location_key = str(request.location_id) if request.location_id is not None else None
        location_encoding = (
            self._location_encoding.get(location_key, self._location_encoding["__global_mean__"])
            if location_key
            else self._location_encoding["__global_mean__"]
        )

        row = {
            "size_marla": request.size_marla,
            "property_type": request.property_type,
            "portion_type": request.portion_type,
            "location_price_encoding": location_encoding,
            "bedrooms": request.bedrooms,
            "bathrooms": request.bathrooms,
            "parking_spaces": request.parking_spaces,
            "is_furnished": request.is_furnished,
            "is_corner": request.is_corner,
            "is_park_facing": request.is_park_facing,
            "has_servant_quarter": request.has_servant_quarter,
            "has_independent_entrance": request.has_independent_entrance,
            "is_newly_built": request.is_newly_built,
        }
        df = pd.DataFrame([row])[FEATURE_COLUMNS]
        for col in CATEGORICAL_FEATURES:
            df[col] = df[col].astype(str)
        return df

    def predict(self, request: PredictionInput, session: Session) -> PredictionResult:
        """Produce a rent estimate for a (possibly unseen) combination.

        Args:
            request: The requested property attributes.
            session: Active DB session, used to fetch similar listings.

        Returns:
            A `PredictionResult` with a point estimate, a model-based
            range from the quantile models, a heuristic confidence score,
            and similar real listings for the caller to sanity-check
            against.

        Raises:
            NoTrainedModelError: If no model has been trained yet.
        """
        self._ensure_loaded()

        X = self._build_feature_row(request)
        estimate = float(self._main_model.predict(X)[0])
        lower = float(self._lower_model.predict(X)[0])
        upper = float(self._upper_model.predict(X)[0])

        minimum, maximum = min(lower, upper), max(lower, upper)

        listing_repo = ListingRepository(session)
        similar = listing_repo.search(
            location_id=request.location_id,
            min_size_marla=request.size_marla * 0.8,
            max_size_marla=request.size_marla * 1.2,
            limit=5,
        )

        relative_range = (maximum - minimum) / max(estimate, 1.0)
        range_confidence = max(0.0, 1 - relative_range)
        evidence_confidence = min(1.0, len(similar) / 5)
        confidence = round(0.6 * range_confidence + 0.4 * evidence_confidence, 2)

        return PredictionResult(
            estimated_price=round(estimate, -2),
            minimum=round(minimum, -2),
            maximum=round(maximum, -2),
            confidence=confidence,
            model_version=self._metadata["model_version"],
            similar_listing_ids=[listing.id for listing in similar],
        )


_service_singleton: PredictionService | None = None


def get_prediction_service() -> PredictionService:
    """FastAPI dependency: a process-wide singleton `PredictionService`."""
    global _service_singleton
    if _service_singleton is None:
        from app.core.config import get_settings

        settings = get_settings()
        _service_singleton = PredictionService(
            models_root=Path("ml/models_registry"), data_root=settings.data_dir
        )
    return _service_singleton
