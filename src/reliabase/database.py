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
    """
    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()
