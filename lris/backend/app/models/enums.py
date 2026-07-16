"""Canonical enums shared across ORM models, the cleaning pipeline, and the
normalization stage.

Defining these once here — rather than as free-floating strings — is what
lets the cleaner/normalizer and the database agree on exactly what values
are valid, and lets CatBoost treat them as proper categorical features
later.
"""

import enum


class PropertyType(str, enum.Enum):
    """Top-level type of the rented property."""

    HOUSE = "house"
    FLAT = "flat"
    PORTION = "portion"
    ROOM = "room"
    UPPER_PORTION = "upper_portion"
    LOWER_PORTION = "lower_portion"
    FARM_HOUSE = "farm_house"
    PENTHOUSE = "penthouse"
    OTHER = "other"


class PortionType(str, enum.Enum):
    """Sub-classification for portion-style rentals (common in Lahore)."""

    FULL_HOUSE = "full_house"
    UPPER_PORTION = "upper_portion"
    LOWER_PORTION = "lower_portion"
    ONE_ROOM = "one_room"
    NOT_APPLICABLE = "not_applicable"


class SizeUnit(str, enum.Enum):
    """Raw unit a listing's size was originally reported in.

    The `Dimension` model always also stores a canonical marla-equivalent
    value regardless of this field, so downstream stages never need to
    convert units themselves.
    """

    MARLA = "marla"
    KANAL = "kanal"
    SQFT = "sqft"
    SQYD = "sqyd"


class Currency(str, enum.Enum):
    """Currency a price was originally listed in.

    Nearly all Lahore listings are PKR, but this keeps the door open for
    future sources without a silent assumption baked into the schema.
    """

    PKR = "PKR"


class SourceName(str, enum.Enum):
    """Registered scrape sources.

    Kept as an enum (rather than a free-text column) so a typo in a
    scraper can't silently create a phantom "source" in the database.
    """

    OLX = "olx"
    ZAMEEN = "zameen"
    GRAANA = "graana"


class ScrapeStatus(str, enum.Enum):
    """Status of a single scrape run, recorded in `ScrapeLog`."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
