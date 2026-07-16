"""Deduplication stage: detect and merge cross-source duplicate listings.

Runs against `Listing` rows already in the database — unlike the earlier
pipeline stages, dedup necessarily needs to compare a new listing against
everything already stored, so it's a repository-backed stage rather than
a pure function.
"""

import logging

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.duplicate import Duplicate
from app.models.listing import Listing

logger = logging.getLogger(__name__)

_WEIGHTS = {"title": 0.4, "description": 0.2, "price": 0.15, "size": 0.15, "location": 0.1}
_MATCH_THRESHOLD = 80.0


def find_duplicate(
    candidate: Listing, session: Session, search_window: int = 200
) -> tuple[Listing, float] | None:
    """Find an existing listing that `candidate` is likely a duplicate of.

    Only compares against listings sharing the candidate's resolved
    location, keeping the search space small instead of scanning the
    whole table (RULES.md performance guidance).

    Args:
        candidate: The newly normalized listing (already flushed).
        session: Active DB session.
        search_window: Max number of same-location listings to compare.

    Returns:
        A `(matched_listing, score)` tuple if the best match clears
        `_MATCH_THRESHOLD`, else None.
    """
    if candidate.location_id is None:
        return None

    stmt = (
        select(Listing)
        .where(Listing.location_id == candidate.location_id, Listing.id != candidate.id)
        .limit(search_window)
    )
    same_location_listings = session.execute(stmt).scalars().all()

    best_match: Listing | None = None
    best_score = 0.0

    for existing in same_location_listings:
        score = _similarity_score(candidate, existing)
        if score > best_score:
            best_score = score
            best_match = existing

    if best_match is not None and best_score >= _MATCH_THRESHOLD:
        logger.info(
            "Listing %s matched existing listing %s with score %.1f",
            candidate.id, best_match.id, best_score,
        )
        return best_match, best_score
    return None


def _similarity_score(a: Listing, b: Listing) -> float:
    """Weighted composite similarity score between two listings, 0-100."""
    title_score = fuzz.token_sort_ratio(a.title or "", b.title or "")
    desc_score = fuzz.token_sort_ratio(a.description or "", b.description or "")
    price_score = _proximity_score(a.current_price, b.current_price, tolerance_pct=0.05)

    a_size = a.dimension.size_marla if a.dimension else None
    b_size = b.dimension.size_marla if b.dimension else None
    size_score = _proximity_score(a_size, b_size, tolerance_pct=0.05)

    location_score = 100.0 if a.location_id == b.location_id else 0.0

    return (
        _WEIGHTS["title"] * title_score
        + _WEIGHTS["description"] * desc_score
        + _WEIGHTS["price"] * price_score
        + _WEIGHTS["size"] * size_score
        + _WEIGHTS["location"] * location_score
    )


def _proximity_score(a: float | None, b: float | None, tolerance_pct: float) -> float:
    """Score how close two numbers are as a 0-100 value.

    100 if identical; decays linearly toward 0 as the relative difference
    grows past `tolerance_pct * 4`.
    """
    if a is None or b is None:
        return 0.0
    if a == 0 and b == 0:
        return 100.0
    relative_diff = abs(a - b) / max(abs(a), abs(b), 1e-9)
    decay_range = tolerance_pct * 4
    return max(0.0, 100.0 * (1 - relative_diff / decay_range))


def merge_duplicate(
    primary: Listing, duplicate: Listing, session: Session, similarity_score: float
) -> Duplicate:
    """Record a duplicate link and migrate the duplicate's price history.

    Neither `Listing` row is deleted (RULES.md §5 / ARCHITECTURE.md §5) —
    `duplicate` is marked inactive so it drops out of active search, while
    its full price history survives, reattached to `primary`.

    Args:
        primary: The listing treated as canonical going forward.
        duplicate: The listing identified as a duplicate of `primary`.
        session: Active DB session.
        similarity_score: The score that triggered this merge, for audit.

    Returns:
        The newly created `Duplicate` link row.
    """
    link = Duplicate(
        primary_listing_id=primary.id,
        duplicate_listing_id=duplicate.id,
        match_method="composite_weighted_similarity",
        similarity_score=similarity_score,
    )
    session.add(link)

    for observation in list(duplicate.price_history):
        observation.listing_id = primary.id

    duplicate.is_active = False
    session.flush()
    return link
