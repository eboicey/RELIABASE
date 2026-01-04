"""Database session management for RELIABASE."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session

from .config import get_engine


@contextmanager
def get_session() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
