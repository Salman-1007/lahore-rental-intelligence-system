"""Parser stage: RawListing -> ParsedListing.

Shared logic only — this stage does NOT know which site a listing came
from. Its job is to validate that required fields are present and pull a
rough numeric price out of free text, since "does this string contain a
number" is universal, not a site-specific quirk. Unit conversion and
attribute extraction (bedrooms, furnished, etc.) belong to the cleaner
stage, not here.
"""

import logging
import re
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SourceName

logger = logging.getLogger(__name__)

# "1.5 lakh", "45,000", "Rs 4.5 Lac", "1 crore" etc.
_MULTIPLIERS = {"lakh": 100_000, "lac": 100_000, "crore": 10_000_000, "k": 1_000}


class ParsedListing(BaseModel):
    """A `RawListing` with a best-effort numeric price extracted.

    Attributes:
        price_numeric: Parsed numeric price, still in whatever currency
            the source uses (assumed PKR for all current sources).
        All other fields are carried over unchanged from `RawListing`.
    """

    source: SourceName
    source_listing_id: str
    source_url: str
    title: str
    description: str | None
    price_numeric: float
    location_raw: str
    size_raw: str | None
    scraped_at: datetime
    extra: dict


class UnparsableListingError(Exception):
    """Raised when a `RawListing` lacks the minimum fields to proceed."""


def parse_raw_listing(raw) -> ParsedListing:  # raw: scrapers.base.dto.RawListing
    """Convert a `RawListing` into a `ParsedListing`.

    Args:
        raw: The scraper's output.

    Returns:
        A `ParsedListing` with a numeric price extracted.

    Raises:
        UnparsableListingError: If title or price text is missing/empty,
            or no numeric price could be extracted at all.
    """
    if not raw.title or not raw.title.strip():
        raise UnparsableListingError(f"Missing title for {raw.source_url}")
    if not raw.price_raw or not raw.price_raw.strip():
        raise UnparsableListingError(f"Missing price for {raw.source_url}")

    price_numeric = _extract_numeric_price(raw.price_raw)
    if price_numeric is None or price_numeric <= 0:
        raise UnparsableListingError(
            f"Could not extract a positive price from {raw.price_raw!r} ({raw.source_url})"
        )

    return ParsedListing(
        source=raw.source,
        source_listing_id=raw.source_listing_id,
        source_url=raw.source_url,
        title=raw.title.strip(),
        description=raw.description.strip() if raw.description else None,
        price_numeric=price_numeric,
        location_raw=raw.location_raw.strip() if raw.location_raw else "",
        size_raw=raw.size_raw,
        scraped_at=raw.scraped_at,
        extra=raw.extra,
    )


def _extract_numeric_price(price_raw: str) -> float | None:
    """Parse a free-text price like 'Rs 45,000' or '4.5 Lac' into a float."""
    text = price_raw.lower().replace(",", "").strip()

    for word, multiplier in _MULTIPLIERS.items():
        match = re.search(rf"([\d.]+)\s*{word}\b", text)
        if match:
            return float(match.group(1)) * multiplier

    match = re.search(r"([\d.]+)", text)
    if match:
        return float(match.group(1))

    return None
