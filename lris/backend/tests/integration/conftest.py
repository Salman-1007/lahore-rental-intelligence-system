"""Shared fixtures for tests that need a real (SQLite, in-memory) database.

Using a fresh in-memory engine per test keeps tests isolated and fast,
while still exercising real SQLAlchemy/ORM behavior instead of mocks —
these are integration tests against the actual schema, per `RULES.md` §6.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models import Base


@pytest.fixture()
def db_session():
    """Yield a `Session` backed by a fresh in-memory SQLite database.

    Tables are created before the test and the engine is discarded after,
    so each test starts from a clean, fully-migrated schema. `StaticPool`
    ensures every connection drawn from this engine shares the same
    in-memory database — without it, each new connection to
    `sqlite:///:memory:` gets its own empty database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()
