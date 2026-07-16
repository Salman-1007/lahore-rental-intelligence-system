"""Normalizer stage: CleanedListing -> NormalizedListing.

The last stage before the database. Two responsibilities: map free-text
property/portion descriptions onto the canonical `PropertyType`/
`PortionType` enums, and resolve the listing's raw location string
against the `Location` hierarchy (creating a best-effort new node if
nothing matches closely enough, per ARCHITECTURE.md §1's location engine).
"""

import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.enums import Currency, PortionType, PropertyType, SizeUnit, SourceName
from app.models.location import Location, LocationLevel
from app.repositories.location_repository import LocationRepository

logger = logging.getLogger(__name__)

_PROPERTY_TYPE_KEYWORDS: list[tuple[str, PropertyType]] = [
    ("upper portion", PropertyType.UPPER_PORTION),
    ("lower portion", PropertyType.LOWER_PORTION),
    ("portion", PropertyType.PORTION),
    ("penthouse", PropertyType.PENTHOUSE),
    ("farm house", PropertyType.FARM_HOUSE),
    ("flat", PropertyType.FLAT),
    ("apartment", PropertyType.FLAT),
    ("room", PropertyType.ROOM),
    ("house", PropertyType.HOUSE),
]

_PORTION_TYPE_KEYWORDS: list[tuple[str, PortionType]] = [
    ("upper portion", PortionType.UPPER_PORTION),
    ("lower portion", PortionType.LOWER_PORTION),
    ("one room", PortionType.ONE_ROOM),
    ("full house", PortionType.FULL_HOUSE),
]


class NormalizedListing(BaseModel):
    """A `CleanedListing` with canonical enums applied and location resolved."""

    source: SourceName
    source_listing_id: str
    source_url: str
    title: str
    description: str | None
    price: float
    currency: Currency
    property_type: PropertyType
    portion_type: PortionType
    location_id: int | None
    location_raw: str
    size_value: float
    size_unit: SizeUnit
    size_marla: float
    bedrooms: int | None
    bathrooms: int | None
    parking_spaces: int
    is_furnished: bool
    is_corner: bool
    is_park_facing: bool
    has_servant_quarter: bool
    has_independent_entrance: bool
    is_newly_built: bool
    scraped_at: datetime
    extra: dict


def normalize_listing(cleaned, session: Session) -> NormalizedListing:
    """Convert a `CleanedListing` into a `NormalizedListing`.

    Args:
        cleaned: Output of the cleaner stage.
        session: Active DB session, needed to resolve/create the location.

    Returns:
        A `NormalizedListing` ready for repository upsert.
    """
    text = " ".join(filter(None, [cleaned.title, cleaned.description])).lower()

    property_type = _match_keyword(text, _PROPERTY_TYPE_KEYWORDS, PropertyType.OTHER)
    portion_type = _match_keyword(text, _PORTION_TYPE_KEYWORDS, PortionType.NOT_APPLICABLE)

    location_id = _resolve_location(cleaned.location_raw, session)

    return NormalizedListing(
        source=cleaned.source,
        source_listing_id=cleaned.source_listing_id,
        source_url=cleaned.source_url,
        title=cleaned.title,
        description=cleaned.description,
        price=cleaned.price,
        currency=Currency.PKR,
        property_type=property_type,
        portion_type=portion_type,
        location_id=location_id,
        location_raw=cleaned.location_raw,
        size_value=cleaned.size_value,
        size_unit=cleaned.size_unit,
        size_marla=cleaned.size_marla,
        bedrooms=cleaned.bedrooms,
        bathrooms=cleaned.bathrooms,
        parking_spaces=cleaned.parking_spaces,
        is_furnished=cleaned.is_furnished,
        is_corner=cleaned.is_corner,
        is_park_facing=cleaned.is_park_facing,
        has_servant_quarter=cleaned.has_servant_quarter,
        has_independent_entrance=cleaned.has_independent_entrance,
        is_newly_built=cleaned.is_newly_built,
        scraped_at=cleaned.scraped_at,
        extra=cleaned.extra,
    )


def _match_keyword(text: str, keyword_map: list[tuple], default):
    for keyword, value in keyword_map:
        if keyword in text:
            return value
    return default


def _resolve_location(location_raw: str, session: Session) -> int | None:
    """Resolve a raw location string to a `Location.id`.

    Tries an exact (case-insensitive) match first, then fuzzy search. If
    nothing matches closely enough, creates a new best-effort `Location`
    node at TOWN level so the listing isn't lost — this node can be
    re-parented/corrected later by the location engine without touching
    any listing rows, since listings reference it only by `location_id`.

    Args:
        location_raw: Free-text location string from the listing.
        session: Active DB session.

    Returns:
        The resolved (or newly created) location's ID, or None if
        `location_raw` is empty/unusable.
    """
    if not location_raw or not location_raw.strip():
        return None

    repo = LocationRepository(session)
    name = location_raw.strip()

    exact = repo.get_by_exact_name(name)
    if exact:
        return exact.id

    fuzzy_matches = repo.fuzzy_search(name, limit=1, score_cutoff=85.0)
    if fuzzy_matches:
        return fuzzy_matches[0].id

    logger.info("No confident location match for %r; creating a new node.", name)
    new_location = repo.add(Location(name=name, level=LocationLevel.TOWN))
    return new_location.id
