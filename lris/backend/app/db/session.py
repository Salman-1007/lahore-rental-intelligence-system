"""Database engine and session management.

This is the ONLY module allowed to construct a SQLAlchemy `Engine`. All
other code obtains a `Session` through `get_db` (FastAPI dependency) or
`session_scope` (scripts/scrapers/pipeline stages).
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped `Session`.

    Yields:
        An open SQLAlchemy session, closed automatically after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for scripts, scrapers, and pipeline stages.

    Commits on success, rolls back and re-raises on any exception.

    Yields:
        An open SQLAlchemy session.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Session rolled back due to an unhandled exception.")
        raise
    finally:
        db.close()
