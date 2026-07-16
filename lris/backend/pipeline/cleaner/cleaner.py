"""Cleaner stage: ParsedListing -> CleanedListing.

Handles the two jobs that are genuinely shared cleaning logic rather than
site-specific parsing: converting whatever size unit a listing was
reported in into a canonical marla value, and extracting structured
boolean/numeric attributes out of free-text descriptions. Per RULES.md,
none of this cares which site the listing came from.
"""

import logging
import re
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SizeUnit, SourceName

logger = logging.getLogger(__name__)

# Punjab urban-area convention: 1 Marla = 225 sq ft, 1 Kanal = 20 Marla.
# Documented here since it's the one "magic number" this whole stage
# depends on — change it in exactly one place if a different regional
# convention is needed.
_SQFT_PER_MARLA = 225.0
_MARLA_PER_KANAL = 20.0
_SQFT_PER_SQYD = 9.0

_UNIT_ALIASES = {
    "marla": SizeUnit.MARLA,
    "kanal": SizeUnit.KANAL,
    "sqft": SizeUnit.SQFT,
    "sq ft": SizeUnit.SQFT,
    "sq.ft": SizeUnit.SQFT,
    "square feet": SizeUnit.SQFT,
    "sqyd": SizeUnit.SQYD,
    "sq yd": SizeUnit.SQYD,
    "square yard": SizeUnit.SQYD,
}


class CleanedListing(BaseModel):
    """A `ParsedListing` with size normalized and attributes extracted."""

    source: SourceName
    source_listing_id: str
    source_url: str
    title: str
    description: str | None
    price: float
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


class UncleanableListingError(Exception):
    """Raised when size cannot be determined at all for a listing."""


def clean_listing(parsed) -> CleanedListing:  # parsed: pipeline.parser.parser.ParsedListing
    """Convert a `ParsedListing` into a `CleanedListing`.

    Args:
        parsed: Output of the parser stage.

    Returns:
        A `CleanedListing` with canonical size and extracted attributes.

    Raises:
        UncleanableListingError: If no size could be determined from
            `size_raw`, the title, or the description.
    """
    size_value, size_unit = _extract_size(
        " ".join(filter(None, [parsed.size_raw, parsed.title, parsed.description]))
    )
    if size_value is None:
        raise UncleanableListingError(f"Could not determine size for {parsed.source_url}")

    size_marla = _to_marla(size_value, size_unit)

    text = " ".join(filter(None, [parsed.title, parsed.description])).lower()

    return CleanedListing(
        source=parsed.source,
        source_listing_id=parsed.source_listing_id,
        source_url=parsed.source_url,
        title=parsed.title,
        description=parsed.description,
        price=parsed.price_numeric,
        location_raw=parsed.location_raw,
        size_value=size_value,
        size_unit=size_unit,
        size_marla=size_marla,
        bedrooms=_extract_count(text, r"(\d+)\s*(?:bed(?:room)?s?)"),
        bathrooms=_extract_count(text, r"(\d+)\s*(?:bath(?:room)?s?|washroom)"),
        parking_spaces=_extract_parking(text),
        is_furnished=_has_keyword(text, ["furnished"]) and not _has_keyword(text, ["unfurnished"]),
        is_corner=_has_keyword(text, ["corner plot", "corner house", "corner "]),
        is_park_facing=_has_keyword(text, ["park facing", "facing park", "park face"]),
        has_servant_quarter=_has_keyword(text, ["servant quarter", "servant room"]),
        has_independent_entrance=_has_keyword(
            text, ["independent entrance", "separate entrance", "own entrance"]
        ),
        is_newly_built=_has_keyword(text, ["newly built", "brand new", "recently built"]),
        scraped_at=parsed.scraped_at,
        extra=parsed.extra,
    )


def _extract_size(text: str) -> tuple[float | None, SizeUnit | None]:
    """Find the first `<number> <unit>` size mention in free text."""
    pattern = r"(\d+(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in _UNIT_ALIASES) + r")\b"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None, None
    value = float(match.group(1))
    unit = _UNIT_ALIASES[match.group(2).lower()]
    return value, unit


def _to_marla(value: float, unit: SizeUnit) -> float:
    """Convert a size value in any supported unit to canonical marla."""
    if unit == SizeUnit.MARLA:
        return value
    if unit == SizeUnit.KANAL:
        return value * _MARLA_PER_KANAL
    if unit == SizeUnit.SQFT:
        return value / _SQFT_PER_MARLA
    if unit == SizeUnit.SQYD:
        return (value * _SQFT_PER_SQYD) / _SQFT_PER_MARLA
    raise ValueError(f"Unsupported size unit: {unit}")


def _extract_count(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_parking(text: str) -> int:
    match = re.search(r"(\d+)\s*(?:car\s*)?parking", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 1 if "parking" in text else 0


def _has_keyword(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)
