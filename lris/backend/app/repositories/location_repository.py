"""Repository for the `Location` hierarchy and its aliases.

Backs both the cleaning/normalization pipeline (resolving free-text
location strings to a canonical `Location` row) and the `/autocomplete`
API endpoint, so both consumers stay in sync on how matching works.
"""

import logging

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.location import Location, LocationAlias
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class LocationRepository(BaseRepository[Location]):
    """Data access for the Lahore location hierarchy."""

    model = Location

    def get_by_exact_name(self, name: str) -> Location | None:
        """Find a location by an exact, case-insensitive name match.

        Args:
            name: The location name to match.

        Returns:
            The matching `Location`, or `None`.
        """
        stmt = select(Location).where(Location.name.ilike(name))
        return self.session.execute(stmt).scalars().first()

    def get_children(self, parent_id: int) -> list[Location]:
        """List the direct children of a location node.

        Args:
            parent_id: Primary key of the parent location.

        Returns:
            All locations whose `parent_id` matches.
        """
        stmt = select(Location).where(Location.parent_id == parent_id)
        return list(self.session.execute(stmt).scalars().all())

    def add_alias(self, location: Location, alias_text: str) -> LocationAlias:
        """Register an alternate spelling/name for a location.

        Args:
            location: The canonical location this alias resolves to.
            alias_text: The alternate text form.

        Returns:
            The newly created `LocationAlias` row.
        """
        alias = LocationAlias(location_id=location.id, alias=alias_text)
        self.session.add(alias)
        self.session.flush()
        return alias

    def fuzzy_search(self, query: str, limit: int = 10, score_cutoff: float = 60.0) -> list[Location]:
        """Fuzzy-match a free-text query against location names and aliases.

        Backs both the normalization pipeline (resolving a scraped
        location string that doesn't exactly match anything on file) and
        the `/autocomplete` endpoint.

        Args:
            query: Free-text search string (e.g. what a user typed, or a
                raw location string a scraper extracted).
            limit: Max number of candidates to return.
            score_cutoff: Minimum RapidFuzz similarity score (0-100) to
                be considered a match at all.

        Returns:
            Matching `Location` rows, best match first.
        """
        stmt = select(Location).options(selectinload(Location.aliases))
        all_locations = list(self.session.execute(stmt).scalars().all())

        if not all_locations:
            return []

        # Build a flat searchable-text -> Location map (canonical name +
        # every alias), so a query can hit either and still resolve to the
        # right canonical row.
        candidates: dict[str, Location] = {}
        for loc in all_locations:
            candidates[loc.name] = loc
            for alias in loc.aliases:
                candidates[alias.alias] = loc

        matches = process.extract(
            query,
            list(candidates.keys()),
            scorer=fuzz.WRatio,
            limit=limit,
            score_cutoff=score_cutoff,
        )

        # Preserve match order, de-duplicate by underlying Location.id in
        # case both a canonical name and one of its aliases matched.
        seen_ids: set[int] = set()
        results: list[Location] = []
        for matched_text, _score, _index in matches:
            loc = candidates[matched_text]
            if loc.id not in seen_ids:
                seen_ids.add(loc.id)
                results.append(loc)
        return results
