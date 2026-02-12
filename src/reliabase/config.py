"""Configuration helpers for RELIABASE.

Reads environment variables for database path and app settings. Defaults to a local
SQLite file for a local-first workflow.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import SQLModel, create_engine

load_dotenv()


def _on_streamlit_cloud() -> bool:
    """Detect Streamlit Cloud (read-only ``/mount/src``)."""
    return os.path.isdir("/mount/src")


def _default_db_path() -> Path:
    """Return a suitable default database file path.

    On Streamlit Cloud the repo checkout (``/mount/src/``) is **read-only**,
    so we place the database in the system temp directory instead.
    """
    explicit = os.getenv("RELIABASE_DB")
    if explicit:
        return Path(explicit).resolve()
    if _on_streamlit_cloud():
        return Path(tempfile.gettempdir()) / "reliabase.sqlite"
    return Path("./reliabase.sqlite").resolve()


DEFAULT_DB_PATH = _default_db_path()

# Module-level engine cache – avoids re-creating the engine on every call.
_engine_cache: dict[str, Any] = {}


def _current_db_url() -> str:
    """Compute the active database URL from environment (avoids stale globals)."""
    return os.getenv("RELIABASE_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def _current_echo() -> bool:
    return os.getenv("RELIABASE_ECHO_SQL", "false").lower() == "true"


def _is_testing() -> bool:
    """Return True when running under pytest (or RELIABASE_TESTING=true)."""
    return os.getenv("RELIABASE_TESTING", "false").lower() == "true"


def get_engine(database_url: str | None = None):
    """Return a cached SQLModel engine configured from env or an override URL.

    The engine is created once per unique ``database_url`` and then reused.
    In application mode we use ``StaticPool`` so the same in-process
    connection is shared (important for Streamlit's single-process model).
    In test mode or on Streamlit Cloud we use ``NullPool`` to avoid
    connection lifetime issues.
    """
    db_url = database_url or _current_db_url()

    if db_url in _engine_cache:
        return _engine_cache[db_url]

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    use_null_pool = _is_testing() or _on_streamlit_cloud()
    engine = create_engine(
        db_url,
        echo=_current_echo(),
        connect_args=connect_args,
        poolclass=NullPool if use_null_pool else StaticPool,
    )
    _engine_cache[db_url] = engine
    return engine


def init_db(engine=None, database_url: str | None = None) -> None:
    """Create database tables if they do not exist.

    Imports :mod:`reliabase.models` first to guarantee every SQLModel
    table class is registered in ``SQLModel.metadata`` before
    ``create_all`` runs.  Without this, an empty database would be
    created and every query would raise ``OperationalError``.
    """
    # Ensure models are registered before creating tables
    import reliabase.models  # noqa: F401

    engine = engine or get_engine(database_url)
    SQLModel.metadata.create_all(engine)
