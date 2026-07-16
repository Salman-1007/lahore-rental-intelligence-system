"""Size/dimension records for a listing.

Kept as its own table (rather than plain columns on `Listing`) so a
listing's size can carry both the unit it was originally reported in AND
a canonical marla-equivalent, without the cleaner needing to know at
insert time which unit the model training code will eventually want.
"""

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import SizeUnit


class Dimension(Base, TimestampMixin):
    """The size of a single listing, in both its original and canonical unit.

    Attributes:
        id: Primary key.
        listing_id: FK to the owning `Listing` (one-to-one).
        original_value: The numeric size as reported by the source.
        original_unit: The unit `original_value` is expressed in.
        size_marla: Canonical size in marla, used uniformly by feature
            engineering regardless of the source's original unit.
    """

    __tablename__ = "dimensions"
    __table_args__ = (
        CheckConstraint("original_value > 0", name="ck_dimension_original_value_positive"),
        CheckConstraint("size_marla > 0", name="ck_dimension_size_marla_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False, unique=True, index=True
    )
    original_value: Mapped[float] = mapped_column(nullable=False)
    original_unit: Mapped[SizeUnit] = mapped_column(SAEnum(SizeUnit), nullable=False)
    size_marla: Mapped[float] = mapped_column(nullable=False, index=True)

    listing: Mapped["Listing"] = relationship(back_populates="dimension")

    def __repr__(self) -> str:
        return f"<Dimension listing_id={self.listing_id} size_marla={self.size_marla}>"
