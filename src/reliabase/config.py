"""Configuration helpers for RELIABASE.

Reads environment variables for database path and app settings. Defaults to a local
SQLite file for a local-first workflow.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import SQLModel, create_engine

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("RELIABASE_DB", "./reliabase.sqlite")).resolve()

# Module-level engine cache – avoids re-creating the engine on every call.
_engine_cache: dict[str, Any] = {}


def _current_db_url() -> str:
    """Compute the active database URL from environment (avoids stale globals)."""
    return os.getenv("RELIABASE_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def _current_echo() -> bool:
    return os.getenv("RELIABASE_ECHO_SQL", "false").lower() == "true"


def _is_testing() -> bool:
    """Return True when running under pytest (or RELIABASE_TESTING=true)."""
    return os.getenv("RELIABASE_TESTING", "false").lower() == "true" or "pytest" in os.getenv("_", "")


def get_engine(database_url: str | None = None):
    """Return a cached SQLModel engine configured from env or an override URL.

    The engine is created once per unique ``database_url`` and then reused.
    In application mode we use ``StaticPool`` so the same in-process
    connection is shared (important for Streamlit's single-process model).
    In test mode we use ``NullPool`` so connections are released promptly.
    """
    db_url = database_url or _current_db_url()

    if db_url in _engine_cache:
        return _engine_cache[db_url]

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    pool = NullPool if _is_testing() else StaticPool
    engine = create_engine(
        db_url,
        echo=_current_echo(),
        connect_args=connect_args,
        poolclass=pool,
    )
    _engine_cache[db_url] = engine
    return engine


def init_db(engine=None, database_url: str | None = None) -> None:
    """Create database tables if they do not exist."""
    engine = engine or get_engine(database_url)
    SQLModel.metadata.create_all(engine)
