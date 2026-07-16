"""Time-series of price observations for a listing.

A listing's price is never overwritten in place — every observation
(including the first) is appended here. This is what lets the `/trends`
endpoint and the EDA stage compute real price movement over time, and
lets deduplication preserve full price history across merged sources.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import Currency


class PriceHistory(Base, TimestampMixin):
    """A single observed price point for a listing at a point in time.

    Attributes:
        id: Primary key.
        listing_id: FK to the owning `Listing`.
        price: Observed price for this record.
        currency: Currency of `price` (normalized to PKR by the cleaner).
        observed_at: When this price was scraped/observed. Distinct from
            `created_at` (row insert time) to preserve the true
            observation timestamp if data is ever backfilled.
    """

    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_price_history_price_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency), default=Currency.PKR, nullable=False
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    listing: Mapped["Listing"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory listing_id={self.listing_id} price={self.price}>"
