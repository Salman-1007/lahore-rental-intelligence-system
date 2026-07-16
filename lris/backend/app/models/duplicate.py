"""Cross-source duplicate links produced by the deduplication stage.

Rather than deleting a listing once it's identified as a duplicate, we
keep both `Listing` rows and record the link here — this is what lets
`price_history` and source attribution survive a merge, per
`ARCHITECTURE.md` §5 and `RULES.md` §5.
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Duplicate(Base, TimestampMixin):
    """A detected duplicate relationship between two `Listing` rows.

    Attributes:
        id: Primary key.
        primary_listing_id: FK to the `Listing` treated as canonical after
            the merge (typically the earliest-seen or highest-quality
            source record).
        duplicate_listing_id: FK to the `Listing` identified as a
            duplicate of the primary.
        match_method: How the match was made (e.g. "exact_title_price",
            "fuzzy_composite_score") — kept as free text since matching
            strategies are expected to evolve during the dedup milestone.
        similarity_score: Numeric confidence score from the matching
            algorithm, for auditing/threshold-tuning later.
    """

    __tablename__ = "duplicates"
    __table_args__ = (
        UniqueConstraint(
            "primary_listing_id", "duplicate_listing_id", name="uq_duplicate_pair"
        ),
        CheckConstraint(
            "primary_listing_id != duplicate_listing_id", name="ck_duplicate_not_self"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    primary_listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False, index=True
    )
    duplicate_listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False, index=True
    )
    match_method: Mapped[str] = mapped_column(String(50), nullable=False)
    similarity_score: Mapped[float] = mapped_column(nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Duplicate primary={self.primary_listing_id} "
            f"duplicate={self.duplicate_listing_id} score={self.similarity_score}>"
        )
