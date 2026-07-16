"""Integration tests for the normalizer stage and the full ingestion pipeline."""

from app.models.enums import PropertyType, SourceName
from app.models.listing import Listing
from app.services.ingestion_service import ingest_raw_listing
from scrapers.base.dto import RawListing


def _raw_listing(**overrides) -> RawListing:
    defaults = dict(
        source=SourceName.OLX,
        source_listing_id="olx-1",
        source_url="https://olx.com.pk/item/1",
        title="5 Marla Portion for rent, 2 bed, furnished",
        description="Nice 5 Marla upper portion in Mustafa Town.",
        price_raw="Rs 45,000",
        location_raw="Mustafa Town",
        size_raw=None,
    )
    defaults.update(overrides)
    return RawListing(**defaults)


def test_ingest_raw_listing_creates_full_row(db_session) -> None:
    """A valid raw listing should produce Listing + Dimension + PropertyDetails rows."""
    is_new = ingest_raw_listing(_raw_listing(), db_session)
    assert is_new is True

    listing = db_session.query(Listing).filter(Listing.source_listing_id == "olx-1").one()
    assert listing.current_price == 45000
    assert listing.dimension.size_marla == 5
    assert listing.property_details.property_type in {
        PropertyType.PORTION,
        PropertyType.UPPER_PORTION,
    }
    assert listing.location is not None
    assert listing.location.name == "Mustafa Town"
    assert len(listing.price_history) == 1


def test_ingest_same_source_listing_twice_does_not_duplicate(db_session) -> None:
    """Re-ingesting the same (source, source_listing_id) should not create a second row."""
    ingest_raw_listing(_raw_listing(), db_session)
    is_new_second_time = ingest_raw_listing(_raw_listing(), db_session)

    assert is_new_second_time is False
    count = db_session.query(Listing).filter(Listing.source_listing_id == "olx-1").count()
    assert count == 1


def test_ingest_price_change_appends_history_not_new_row(db_session) -> None:
    """A price change on re-ingestion should append to history, not duplicate the listing."""
    ingest_raw_listing(_raw_listing(), db_session)
    ingest_raw_listing(_raw_listing(price_raw="Rs 48,000"), db_session)

    listing = db_session.query(Listing).filter(Listing.source_listing_id == "olx-1").one()
    assert listing.current_price == 48000
    assert len(listing.price_history) == 2


def test_ingest_unparsable_listing_returns_false(db_session) -> None:
    """A listing with no extractable size should be skipped, not crash the run."""
    is_new = ingest_raw_listing(
        _raw_listing(
            source_listing_id="olx-2",
            title="Nice place",
            description="No size mentioned",
        ),
        db_session,
    )
    assert is_new is False


def test_cross_source_duplicate_is_merged(db_session) -> None:
    """Two near-identical listings from different sources should merge."""
    ingest_raw_listing(
        _raw_listing(
            source=SourceName.OLX,
            source_listing_id="olx-3",
            title="5 Marla Portion for rent in Mustafa Town, 2 bed",
            description="Nice 5 Marla upper portion in Mustafa Town furnished.",
            price_raw="Rs 45,000",
        ),
        db_session,
    )
    ingest_raw_listing(
        _raw_listing(
            source=SourceName.ZAMEEN,
            source_listing_id="zm-3",
            title="5 Marla Portion for rent in Mustafa Town, 2 bed",
            description="Nice 5 Marla upper portion in Mustafa Town furnished.",
            price_raw="Rs 46,000",
        ),
        db_session,
    )

    active_listings = (
        db_session.query(Listing)
        .filter(Listing.is_active.is_(True), Listing.location.has(name="Mustafa Town"))
        .all()
    )
    assert len(active_listings) == 1
