"""Generic base repository.

Concrete repositories (`ListingRepository`, `LocationRepository`, ...)
inherit from this for the handful of operations that are truly identical
across aggregates. Anything aggregate-specific (composite lookups,
upserts with business rules) is defined on the concrete repository, never
bolted onto this base as a generic `execute_query` escape hatch — see
`RULES.md` §3.
"""

import logging
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

logger = logging.getLogger(__name__)


class BaseRepository(Generic[ModelType]):
    """Shared CRUD operations for a single ORM model.

    Attributes:
        model: The ORM model class this repository manages.
        session: The SQLAlchemy session injected at construction time
            (dependency injection — see `RULES.md` §3).
    """

    model: type[ModelType]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, entity_id: int) -> ModelType | None:
        """Fetch a single row by primary key.

        Args:
            entity_id: Primary key value to look up.

        Returns:
            The matching row, or `None` if it doesn't exist.
        """
        return self.session.get(self.model, entity_id)

    def add(self, entity: ModelType) -> ModelType:
        """Stage a new row for insert and flush to obtain its primary key.

        Args:
            entity: A constructed, unsaved ORM instance.

        Returns:
            The same instance, refreshed with its assigned primary key.
        """
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        """Delete a row.

        Args:
            entity: The ORM instance to remove.
        """
        self.session.delete(entity)
        self.session.flush()
