"""The canonical listing record — one row per deduplicated rental property.

This is the aggregate root of the schema. It intentionally stays lean:
identity, source linkage, location, current price, and a raw-text
description. Everything the cleaner *infers* lives in `PropertyDetails`;
everything about size lives in `Dimension`; every price ever observed
lives in `PriceHistory`. This split is what keeps each concern editable
independently (see `RULES.md` §2).
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import SourceName


class Listing(Base, TimestampMixin):
    """A single rental listing, deduplicated across sources.

    Attributes:
        id: Primary key.
        source_id: FK to the `Source` this listing was scraped from. If a
            listing is later found to be a duplicate of one from another
            source, the merge is recorded in `Duplicate`, not by mutating
            this field.
        source_listing_id: The source site's own identifier for this
            listing (e.g. OLX ad ID), used for dedup-on-insert within a
            single source.
        source_url: Direct URL to the original listing.
        title: Raw listing title as scraped.
        description: Raw listing description as scraped (the cleaner reads
            from this; it is never mutated in place).
        location_id: FK to the resolved `Location`.
        current_price: Latest known price (denormalized from
            `PriceHistory` for fast search/sort; the history table remains
            the source of truth).
        is_active: Whether the listing still appears live on the source
            site (set to False when a scrape run no longer finds it).
        first_seen_at: When this listing was first scraped.
        last_seen_at: When this listing was last confirmed present on
            the source site.
    """

    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "source_listing_id", name="uq_listing_source_source_listing_id"
        ),
        CheckConstraint("current_price > 0", name="ck_listing_current_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    location_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True, index=True
    )

    current_price: Mapped[float] = mapped_column(nullable=False, index=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(nullable=False)

    source: Mapped["Source"] = relationship(back_populates="listings")
    location: Mapped["Location | None"] = relationship(back_populates="listings")

    property_details: Mapped["PropertyDetails | None"] = relationship(
        back_populates="listing", cascade="all, delete-orphan", uselist=False
    )
    dimension: Mapped["Dimension | None"] = relationship(
        back_populates="listing", cascade="all, delete-orphan", uselist=False
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Listing id={self.id} title={self.title[:40]!r} price={self.current_price}>"
