"""Shared DTO every scraper must emit, regardless of source.

Per RULES.md, site-specific parsing logic never leaks past this boundary:
an `OLXScraper` and a `ZameenScraper` both produce exactly this shape, and
nothing downstream (parser/cleaner/normalizer) needs to know which site a
`RawListing` came from except via the `source` field.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.enums import SourceName


class RawListing(BaseModel):
    """Exactly what a scraper extracted, with minimal transformation.

    All text fields are kept as close to the source's raw text as
    possible — unit conversion, currency parsing, and attribute
    extraction happen later (parser/cleaner stages), not here.
    """

    source: SourceName
    source_listing_id: str
    source_url: str
    title: str
    description: str | None = None
    price_raw: str
    location_raw: str
    size_raw: str | None = None
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict = Field(default_factory=dict)
