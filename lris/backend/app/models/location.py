"""Lahore location hierarchy: City -> Town -> Phase -> Block -> Street.

Modeled as a self-referential adjacency list rather than five separate
tables, because the depth of the hierarchy varies by area (some listings
resolve only to Town level, others down to Street level), and a single
table with a `parent_id` handles that variability without a rigid schema.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LocationLevel:
    """String constants for the `level` column.

    Not an `enum.Enum` (unlike other categorical fields) because the
    location engine's fuzzy-matching and alias-generation code treats
    levels as plain strings when building hierarchy paths — an enum would
    add friction there for no schema-safety benefit, since level values
    are only ever set by the location engine itself, not by scrapers.
    """

    CITY = "city"
    TOWN = "town"
    PHASE = "phase"
    BLOCK = "block"
    STREET = "street"


class Location(Base, TimestampMixin):
    """A single node in the Lahore location hierarchy.

    Attributes:
        id: Primary key.
        name: Canonical name of this node (e.g. "Mustafa Town").
        level: One of `LocationLevel` — city/town/phase/block/street.
        parent_id: Self-referential FK to the containing location, null
            for the city root.
        latitude: Optional coordinate, used for distance-based features.
        longitude: Optional coordinate, used for distance-based features.
    """

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("locations.id"), nullable=True, index=True
    )
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    parent: Mapped["Location | None"] = relationship(
        remote_side="Location.id", back_populates="children"
    )
    children: Mapped[list["Location"]] = relationship(back_populates="parent")

    aliases: Mapped[list["LocationAlias"]] = relationship(
        back_populates="location", cascade="all, delete-orphan"
    )
    listings: Mapped[list["Listing"]] = relationship(back_populates="location")

    def __repr__(self) -> str:
        return f"<Location id={self.id} name={self.name!r} level={self.level}>"


class LocationAlias(Base, TimestampMixin):
    """An alternate spelling/name that should resolve to a `Location`.

    Populated by the location engine (e.g. "DHA Phase 5" / "DHA Ph 5" /
    "Defence Phase 5" all pointing at the same `Location` row), which is
    what makes fuzzy search and autocomplete robust to how differently
    each source spells the same place.

    Attributes:
        id: Primary key.
        location_id: FK to the canonical `Location` this alias resolves to.
        alias: The alternate text form.
    """

    __tablename__ = "location_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    location: Mapped["Location"] = relationship(back_populates="aliases")

    def __repr__(self) -> str:
        return f"<LocationAlias id={self.id} alias={self.alias!r}>"
