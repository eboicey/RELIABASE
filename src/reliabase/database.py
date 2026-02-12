"""Database session management for RELIABASE."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session

from .config import get_engine


@contextmanager
def get_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    The engine is cached by :func:`config.get_engine`, so we never
    dispose it here – that would destroy the shared connection pool.

    ``expire_on_commit=False`` keeps loaded attributes accessible after
    commit, which prevents ``DetachedInstanceError`` when ORM objects are
    used outside (after) the session context manager.
    """
    engine = get_engine()
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            session.close()
