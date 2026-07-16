"""Declarative base and shared mixins for all ORM models.

Every model in `app/models/` inherits from `Base`, and picks up
`TimestampMixin` when it needs `created_at`/`updated_at` tracking. Keeping
this in one place means schema-wide conventions (naming, timestamp
behavior) change in exactly one file.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    """Return a timezone-aware current UTC timestamp.

    Used as the default/onupdate callable for timestamp columns instead of
    `datetime.utcnow`, which is deprecated and naive.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the project."""


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns to a model.

    Attributes:
        created_at: Set once, at insert time.
        updated_at: Refreshed on every update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
