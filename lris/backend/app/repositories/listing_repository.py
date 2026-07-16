"""Repository for the `Listing` aggregate.

This is the only place allowed to construct queries against `Listing`,
`Dimension`, `PropertyDetails`, and `PriceHistory` as a unit — services
(and eventually the scrapers' insertion step) call methods here, never
raw `session.query(...)` directly (see `RULES.md` §2).
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.dimension import Dimension
from app.models.enums import SourceName
from app.models.listing import Listing
from app.models.price_history import PriceHistory
from app.models.property_details import PropertyDetails
from app.models.source import Source
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ListingRepository(BaseRepository[Listing]):
    """Data access for `Listing` and its directly-owned child records."""

    model = Listing

    def get_by_source_listing_id(
        self, source_name: SourceName, source_listing_id: str
    ) -> Listing | None:
        """Look up a listing by its originating source and source-side ID.

        Used by scrapers to decide whether an incoming raw listing is a
        new insert or an update to an existing row (dedup-on-insert within
        a single source, per `RULES.md` §4).

        Args:
            source_name: Which source site the listing came from.
            source_listing_id: The source site's own identifier.

        Returns:
            The matching `Listing`, or `None` if it hasn't been seen
            before from this source.
        """
        stmt = (
            select(Listing)
            .join(Source, Listing.source_id == Source.id)
            .where(
                Source.name == source_name,
                Listing.source_listing_id == source_listing_id,
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_with_details(self, listing_id: int) -> Listing | None:
        """Fetch a listing eagerly loaded with dimension/details/price history.

        Args:
            listing_id: Primary key of the listing.

        Returns:
            The `Listing` with related rows already loaded (avoids N+1
            queries when the caller needs the full aggregate), or `None`.
        """
        stmt = (
            select(Listing)
            .where(Listing.id == listing_id)
            .options(
                selectinload(Listing.dimension),
                selectinload(Listing.property_details),
                selectinload(Listing.price_history),
                selectinload(Listing.location),
            )
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def record_price_observation(
        self, listing: Listing, price: float, observed_at: datetime
    ) -> PriceHistory:
        """Append a new price observation and update the listing's current price.

        Never overwrites a prior `PriceHistory` row — see `RULES.md` §5 on
        never overwriting historical data.

        Args:
            listing: The listing this observation belongs to.
            price: The newly observed price.
            observed_at: When this price was observed.

        Returns:
            The newly created `PriceHistory` row.
        """
        observation = PriceHistory(listing_id=listing.id, price=price, observed_at=observed_at)
        self.session.add(observation)
        listing.current_price = price
        listing.last_seen_at = observed_at
        self.session.flush()
        return observation

    def search(
        self,
        *,
        location_id: int | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        min_size_marla: float | None = None,
        max_size_marla: float | None = None,
        bedrooms: int | None = None,
        property_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Listing]:
        """Search active listings against common filter criteria.

        Args:
            location_id: Restrict to a specific resolved location.
            min_price: Minimum current price, inclusive.
            max_price: Maximum current price, inclusive.
            min_size_marla: Minimum canonical size, inclusive.
            max_size_marla: Maximum canonical size, inclusive.
            bedrooms: Exact bedroom count match.
            property_type: Exact property type match (e.g. "portion").
            limit: Max rows to return.
            offset: Rows to skip, for pagination.

        Returns:
            Matching, currently-active listings.
        """
        stmt = select(Listing).where(Listing.is_active.is_(True))

        if location_id is not None:
            stmt = stmt.where(Listing.location_id == location_id)
        if min_price is not None:
            stmt = stmt.where(Listing.current_price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Listing.current_price <= max_price)
        if min_size_marla is not None or max_size_marla is not None:
            stmt = stmt.join(Dimension, Dimension.listing_id == Listing.id)
            if min_size_marla is not None:
                stmt = stmt.where(Dimension.size_marla >= min_size_marla)
            if max_size_marla is not None:
                stmt = stmt.where(Dimension.size_marla <= max_size_marla)
        if bedrooms is not None or property_type is not None:
            stmt = stmt.join(PropertyDetails, PropertyDetails.listing_id == Listing.id)
            if bedrooms is not None:
                stmt = stmt.where(PropertyDetails.bedrooms == bedrooms)
            if property_type is not None:
                stmt = stmt.where(PropertyDetails.property_type == property_type)

        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())
