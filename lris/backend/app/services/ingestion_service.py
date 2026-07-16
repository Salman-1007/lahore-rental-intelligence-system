"""Ingestion service: RawListing -> Parser -> Cleaner -> Normalizer ->
repository upsert -> dedup, as a single unit a scraper calls per listing.

This is the only place that calls all four pipeline stages in sequence,
so a scraper's `on_listing` callback stays a one-line call into this
module rather than re-implementing orchestration itself.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.dimension import Dimension
from app.models.listing import Listing
from app.models.property_details import PropertyDetails
from app.models.source import Source
from app.repositories.listing_repository import ListingRepository
from pipeline.cleaner.cleaner import UncleanableListingError, clean_listing
from pipeline.dedup.dedup import find_duplicate, merge_duplicate
from pipeline.normalizer.normalizer import normalize_listing
from pipeline.parser.parser import UnparsableListingError, parse_raw_listing

logger = logging.getLogger(__name__)


def ingest_raw_listing(raw, session: Session) -> bool:
    """Run one `RawListing` through the full pipeline and store it.

    Args:
        raw: The scraper's output (`scrapers.base.dto.RawListing`).
        session: Active DB session (caller manages transaction scope).

    Returns:
        True if this resulted in a new, non-duplicate `Listing` row;
        False if it was skipped (unparsable/uncleanable), matched an
        existing row from the same source, or matched a cross-source
        duplicate.
    """
    try:
        parsed = parse_raw_listing(raw)
        cleaned = clean_listing(parsed)
    except (UnparsableListingError, UncleanableListingError) as exc:
        logger.warning("Skipping listing %s: %s", raw.source_url, exc)
        return False

    normalized = normalize_listing(cleaned, session)
    listing_repo = ListingRepository(session)

    existing = listing_repo.get_by_source_listing_id(
        normalized.source, normalized.source_listing_id
    )
    if existing is not None:
        if existing.current_price != normalized.price:
            listing_repo.record_price_observation(
                existing, normalized.price, datetime.now(timezone.utc)
            )
        existing.last_seen_at = datetime.now(timezone.utc)
        return False

    source = _get_or_create_source(session, normalized.source)
    now = datetime.now(timezone.utc)

    listing = listing_repo.add(
        Listing(
            source_id=source.id,
            source_listing_id=normalized.source_listing_id,
            source_url=normalized.source_url,
            title=normalized.title,
            description=normalized.description,
            location_id=normalized.location_id,
            current_price=normalized.price,
            first_seen_at=now,
            last_seen_at=now,
        )
    )

    session.add(
        Dimension(
            listing_id=listing.id,
            original_value=normalized.size_value,
            original_unit=normalized.size_unit,
            size_marla=normalized.size_marla,
        )
    )
    session.add(
        PropertyDetails(
            listing_id=listing.id,
            property_type=normalized.property_type,
            portion_type=normalized.portion_type,
            bedrooms=normalized.bedrooms,
            bathrooms=normalized.bathrooms,
            parking_spaces=normalized.parking_spaces,
            is_furnished=normalized.is_furnished,
            is_corner=normalized.is_corner,
            is_park_facing=normalized.is_park_facing,
            has_servant_quarter=normalized.has_servant_quarter,
            has_independent_entrance=normalized.has_independent_entrance,
            is_newly_built=normalized.is_newly_built,
        )
    )
    listing_repo.record_price_observation(listing, normalized.price, now)
    session.flush()

    match = find_duplicate(listing, session)
    if match is not None:
        matched_listing, score = match
        merge_duplicate(matched_listing, listing, session, similarity_score=score)
        return False

    return True


def _get_or_create_source(session: Session, source_name) -> Source:
    source = session.query(Source).filter(Source.name == source_name).one_or_none()
    if source is None:
        source = Source(name=source_name, display_name=source_name.value.title(), base_url="")
        session.add(source)
        session.flush()
    return source
