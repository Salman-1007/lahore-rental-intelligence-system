"""Integration tests for `ListingRepository` against a real SQLite schema."""

from datetime import datetime, timezone

from app.models.dimension import Dimension
from app.models.enums import PropertyType, SizeUnit, SourceName
from app.models.listing import Listing
from app.models.property_details import PropertyDetails
from app.models.source import Source
from app.repositories.listing_repository import ListingRepository


def _make_source(session, name: SourceName = SourceName.OLX) -> Source:
    source = Source(name=name, display_name=name.value.title(), base_url="https://example.com")
    session.add(source)
    session.flush()
    return source


def test_add_and_get_by_id(db_session) -> None:
    """A listing added via the repository should be retrievable by id."""
    repo = ListingRepository(db_session)
    source = _make_source(db_session)
    now = datetime.now(timezone.utc)

    listing = repo.add(
        Listing(
            source_id=source.id,
            source_listing_id="abc123",
            source_url="https://example.com/abc123",
            title="5 Marla Portion for rent",
            current_price=45000,
            first_seen_at=now,
            last_seen_at=now,
        )
    )

    fetched = repo.get_by_id(listing.id)
    assert fetched is not None
    assert fetched.title == "5 Marla Portion for rent"


def test_get_by_source_listing_id_dedups_within_source(db_session) -> None:
    """Looking up an existing (source, source_listing_id) pair should find it."""
    repo = ListingRepository(db_session)
    source = _make_source(db_session, SourceName.ZAMEEN)
    now = datetime.now(timezone.utc)

    repo.add(
        Listing(
            source_id=source.id,
            source_listing_id="zm-999",
            source_url="https://zameen.com/zm-999",
            title="10 Marla House",
            current_price=90000,
            first_seen_at=now,
            last_seen_at=now,
        )
    )

    found = repo.get_by_source_listing_id(SourceName.ZAMEEN, "zm-999")
    assert found is not None
    assert found.title == "10 Marla House"

    not_found = repo.get_by_source_listing_id(SourceName.ZAMEEN, "does-not-exist")
    assert not_found is None


def test_record_price_observation_appends_history_and_updates_current(db_session) -> None:
    """Recording a new price should append to history, not overwrite it."""
    repo = ListingRepository(db_session)
    source = _make_source(db_session)
    now = datetime.now(timezone.utc)

    listing = repo.add(
        Listing(
            source_id=source.id,
            source_listing_id="abc456",
            source_url="https://example.com/abc456",
            title="Upper Portion",
            current_price=30000,
            first_seen_at=now,
            last_seen_at=now,
        )
    )

    repo.record_price_observation(listing, price=32000, observed_at=now)

    assert listing.current_price == 32000
    assert len(listing.price_history) == 1
    assert listing.price_history[0].price == 32000


def test_search_filters_by_size_and_bedrooms(db_session) -> None:
    """Search should correctly join Dimension/PropertyDetails when filtered."""
    repo = ListingRepository(db_session)
    source = _make_source(db_session)
    now = datetime.now(timezone.utc)

    listing = repo.add(
        Listing(
            source_id=source.id,
            source_listing_id="search-1",
            source_url="https://example.com/search-1",
            title="5 Marla Portion, 2 bed",
            current_price=40000,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    db_session.add(Dimension(listing_id=listing.id, original_value=5, original_unit=SizeUnit.MARLA, size_marla=5))
    db_session.add(
        PropertyDetails(listing_id=listing.id, property_type=PropertyType.PORTION, bedrooms=2)
    )
    db_session.flush()

    results = repo.search(min_size_marla=4, max_size_marla=6, bedrooms=2)
    assert len(results) == 1
    assert results[0].id == listing.id

    no_match = repo.search(bedrooms=5)
    assert no_match == []
