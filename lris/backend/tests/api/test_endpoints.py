"""API tests for /search, /autocomplete, /listings, /stats, /trends.

`/predict` is exercised lightly since it depends on a trained model
artifact, which these tests don't produce.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.models.enums import SourceName
from app.services.ingestion_service import ingest_raw_listing
from scrapers.base.dto import RawListing


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def _get_test_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_test_db

    with Session(engine) as seed_session:
        ingest_raw_listing(
            RawListing(
                source=SourceName.OLX,
                source_listing_id="api-1",
                source_url="https://olx.com.pk/item/api-1",
                title="5 Marla Portion for rent, 2 bed",
                description="Nice 5 Marla upper portion in Mustafa Town.",
                price_raw="Rs 45,000",
                location_raw="Mustafa Town",
            ),
            seed_session,
        )
        seed_session.commit()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


def test_search_returns_seeded_listing(client) -> None:
    response = client.get("/api/v1/search")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"].startswith("5 Marla Portion")


def test_search_filters_by_min_price_excludes_below_threshold(client) -> None:
    response = client.get("/api/v1/search", params={"min_price": 100000})
    assert response.status_code == 200
    assert response.json() == []


def test_autocomplete_finds_seeded_location(client) -> None:
    response = client.get("/api/v1/autocomplete", params={"q": "Mustafa"})
    assert response.status_code == 200
    body = response.json()
    assert any(loc["name"] == "Mustafa Town" for loc in body)


def test_get_listing_by_id(client) -> None:
    search_response = client.get("/api/v1/search")
    listing_id = search_response.json()[0]["id"]

    response = client.get(f"/api/v1/listings/{listing_id}")
    assert response.status_code == 200
    assert response.json()["id"] == listing_id


def test_get_listing_404_for_unknown_id(client) -> None:
    response = client.get("/api/v1/listings/999999")
    assert response.status_code == 404


def test_stats_endpoint_reflects_seeded_data(client) -> None:
    response = client.get("/api/v1/stats")
    assert response.status_code == 200
    body = response.json()
    assert body["total_listings"] == 1
    assert body["active_listings"] == 1
    assert body["average_price"] == 45000


def test_trends_endpoint_returns_a_point(client) -> None:
    response = client.get("/api/v1/trends")
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 1


def test_predict_without_trained_model_returns_503(client) -> None:
    response = client.post(
        "/api/v1/predict",
        json={"property_type": "portion", "size_marla": 5, "location_name": "Mustafa Town"},
    )
    assert response.status_code == 503
