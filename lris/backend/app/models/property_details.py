"""Structured attributes extracted from a listing's description by the
cleaning stage (bedrooms, bathrooms, furnished, corner, etc).

Kept separate from `Listing` itself so the core listing record stays
focused on identity/price/location, while everything the cleaner
*infers* from free text lives in one clearly-labeled place.
"""

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import PortionType, PropertyType


class PropertyDetails(Base, TimestampMixin):
    """Extracted/normalized structured attributes for one listing.

    Attributes:
        id: Primary key.
        listing_id: FK to the owning `Listing` (one-to-one).
        property_type: Canonical property type.
        portion_type: Canonical portion sub-type, if applicable.
        bedrooms: Extracted bedroom count.
        bathrooms: Extracted bathroom count.
        parking_spaces: Extracted parking space count (0 if none mentioned).
        is_furnished: Whether the description indicates furnished.
        is_corner: Whether the description indicates a corner plot.
        is_park_facing: Whether the description indicates park-facing.
        has_servant_quarter: Whether a servant quarter is mentioned.
        has_independent_entrance: Whether an independent entrance is mentioned.
        is_newly_built: Whether the description indicates a new/recent build.
    """

    __tablename__ = "property_details"
    __table_args__ = (
        CheckConstraint("bedrooms >= 0", name="ck_property_details_bedrooms_nonneg"),
        CheckConstraint("bathrooms >= 0", name="ck_property_details_bathrooms_nonneg"),
        CheckConstraint("parking_spaces >= 0", name="ck_property_details_parking_nonneg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(
        ForeignKey("listings.id"), nullable=False, unique=True, index=True
    )

    property_type: Mapped[PropertyType] = mapped_column(nullable=False, index=True)
    portion_type: Mapped[PortionType] = mapped_column(
        nullable=False, default=PortionType.NOT_APPLICABLE
    )

    bedrooms: Mapped[int | None] = mapped_column(nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(nullable=True)
    parking_spaces: Mapped[int] = mapped_column(default=0, nullable=False)

    is_furnished: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_corner: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_park_facing: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_servant_quarter: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_independent_entrance: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_newly_built: Mapped[bool] = mapped_column(default=False, nullable=False)

    listing: Mapped["Listing"] = relationship(back_populates="property_details")

    def __repr__(self) -> str:
        return (
            f"<PropertyDetails listing_id={self.listing_id} "
            f"property_type={self.property_type.value}>"
        )
