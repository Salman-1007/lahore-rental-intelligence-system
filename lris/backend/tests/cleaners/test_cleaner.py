"""Unit tests for the cleaner stage (unit parsing + attribute extraction)."""

import pytest

from app.models.enums import SizeUnit, SourceName
from pipeline.cleaner.cleaner import UncleanableListingError, clean_listing
from pipeline.parser.parser import parse_raw_listing
from scrapers.base.dto import RawListing


def _raw(**overrides) -> RawListing:
    defaults = dict(
        source=SourceName.OLX,
        source_listing_id="1",
        source_url="https://example.com/1",
        title="5 Marla Portion for rent, 2 bed 2 bath, furnished, corner",
        description="Beautiful 5 Marla upper portion, newly built, servant quarter available.",
        price_raw="Rs 45,000",
        location_raw="Mustafa Town",
        size_raw=None,
    )
    defaults.update(overrides)
    return RawListing(**defaults)


def test_clean_listing_converts_marla_correctly() -> None:
    parsed = parse_raw_listing(_raw())
    cleaned = clean_listing(parsed)
    assert cleaned.size_unit == SizeUnit.MARLA
    assert cleaned.size_marla == 5


def test_clean_listing_converts_kanal_to_marla() -> None:
    raw = _raw(title="1 Kanal House for rent", description="Spacious 1 Kanal house.")
    parsed = parse_raw_listing(raw)
    cleaned = clean_listing(parsed)
    assert cleaned.size_marla == 20


def test_clean_listing_converts_sqft_to_marla() -> None:
    raw = _raw(title="900 sqft flat for rent", description="Nice flat, 900 sq ft.")
    parsed = parse_raw_listing(raw)
    cleaned = clean_listing(parsed)
    assert cleaned.size_marla == pytest.approx(4.0, rel=0.01)


def test_clean_listing_extracts_bedrooms_and_bathrooms() -> None:
    parsed = parse_raw_listing(_raw())
    cleaned = clean_listing(parsed)
    assert cleaned.bedrooms == 2
    assert cleaned.bathrooms == 2


def test_clean_listing_extracts_boolean_attributes() -> None:
    parsed = parse_raw_listing(_raw())
    cleaned = clean_listing(parsed)
    assert cleaned.is_furnished is True
    assert cleaned.is_corner is True
    assert cleaned.is_newly_built is True
    assert cleaned.has_servant_quarter is True
    assert cleaned.is_park_facing is False


def test_clean_listing_unfurnished_is_not_furnished() -> None:
    raw = _raw(title="5 Marla unfurnished portion", description="Not furnished at all.")
    parsed = parse_raw_listing(raw)
    cleaned = clean_listing(parsed)
    assert cleaned.is_furnished is False


def test_clean_listing_raises_when_no_size_found() -> None:
    raw = _raw(title="Nice place for rent", description="No size mentioned here.")
    parsed = parse_raw_listing(raw)
    with pytest.raises(UncleanableListingError):
        clean_listing(parsed)


def test_parser_extracts_lakh_price() -> None:
    raw = _raw(price_raw="4.5 Lac")
    parsed = parse_raw_listing(raw)
    assert parsed.price_numeric == 450_000
