"""End-to-end smoke test: dataset build -> train -> predict.

Uses synthetic listings inserted through the real ingestion pipeline
(never presented as real data) purely to verify the ML pipeline's
mechanics run without error: dataset versioning writes real files,
CatBoost actually trains, and the prediction service loads what training
produced and returns a sane result. This is NOT a model-quality test.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base
from app.models.enums import SourceName
from app.services.ingestion_service import ingest_raw_listing
from app.services.prediction_service import PredictionInput, PredictionService
from ml.datasets.dataset_builder import build_dataset
from ml.training.train import train_model
from scrapers.base.dto import RawListing

LOCATIONS = ["Mustafa Town", "DHA Phase 5", "Johar Town", "Wapda Town"]


@pytest.fixture()
def tmp_data_root(tmp_path) -> Path:
    root = tmp_path / "data"
    for stage in ["raw", "clean", "processed", "training", "validation"]:
        (root / stage).mkdir(parents=True)
    return root


@pytest.fixture()
def seeded_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    TEMPLATES = [
        "{size} Marla {kind} available for rent right away",
        "For rent: spacious {size} marla {kind}, great location",
        "{kind} of {size} marla up for immediate rent",
        "Rent this lovely {size} marla {kind} today",
    ]
    KINDS = ["portion", "house", "flat"]

    with Session(engine) as session:
        listing_index = 0
        for location in LOCATIONS:
            for size in [3, 5, 7, 9, 11, 13, 15, 17, 19]:
                kind = KINDS[listing_index % len(KINDS)]
                template = TEMPLATES[listing_index % len(TEMPLATES)]
                title = template.format(size=size, kind=kind)
                price = 15000 + (LOCATIONS.index(location) * 20000) + size * 4000
                bedrooms = 1 + (listing_index % 4)
                ingest_raw_listing(
                    RawListing(
                        source=SourceName.OLX if listing_index % 2 == 0 else SourceName.ZAMEEN,
                        source_listing_id=f"synthetic-{listing_index}",
                        source_url=f"https://example.com/{listing_index}",
                        title=f"{title}, {bedrooms} bed 1 bath, furnished",
                        description=(
                            f"A {kind} measuring {size} marla situated in {location}, "
                            "with dedicated parking and modern fittings."
                        ),
                        price_raw=f"Rs {price}",
                        location_raw=location,
                        scraped_at=datetime.now(timezone.utc) - timedelta(days=listing_index),
                    ),
                    session,
                )
                listing_index += 1
        session.commit()
        yield session

    engine.dispose()


def test_full_ml_pipeline_runs_end_to_end(tmp_data_root, seeded_session) -> None:
    """build_dataset -> train_model -> PredictionService.predict should all succeed."""
    dataset_version = build_dataset(seeded_session, tmp_data_root)
    assert dataset_version.row_counts["clean"] >= 20

    models_root = tmp_data_root.parent / "models_registry"
    trained = train_model(dataset_version.version, tmp_data_root, models_root)
    assert trained.main_model_path.exists()
    assert trained.evaluation_path.exists()

    eval_report = json.loads(trained.evaluation_path.read_text())
    assert "mae" in eval_report["metrics"]
    assert "rmse" in eval_report["metrics"]

    service = PredictionService(models_root=models_root, data_root=tmp_data_root)
    result = service.predict(
        PredictionInput(
            property_type="portion",
            portion_type="upper_portion",
            size_marla=6,
            location_id=1,
            bedrooms=2,
            bathrooms=1,
            is_furnished=True,
        ),
        seeded_session,
    )

    assert result.estimated_price > 0
    assert result.minimum <= result.estimated_price <= result.maximum
    assert 0.0 <= result.confidence <= 1.0
