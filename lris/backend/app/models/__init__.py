"""Model registry.

Importing this module guarantees every ORM model is registered on the
shared `Base.metadata` — required for `Base.metadata.create_all()` in
tests and for Alembic's `--autogenerate` to see the full schema.

Import order matters only in that every model referenced by a string in a
`relationship()` call must be importable by the time SQLAlchemy configures
mappers; since Python resolves those lazily on first use (not at class
definition time), a flat import list here is sufficient - no manual
ordering required.
"""

from app.models.base import Base
from app.models.dimension import Dimension
from app.models.duplicate import Duplicate
from app.models.listing import Listing
from app.models.location import Location, LocationAlias
from app.models.price_history import PriceHistory
from app.models.property_details import PropertyDetails
from app.models.scrape_log import ScrapeLog
from app.models.source import Source

__all__ = [
    "Base",
    "Dimension",
    "Duplicate",
    "Listing",
    "Location",
    "LocationAlias",
    "PriceHistory",
    "PropertyDetails",
    "ScrapeLog",
    "Source",
]
