"""Configuration helpers for RELIABASE.

Reads environment variables for database path and app settings. Defaults to a local
SQLite file for a local-first workflow.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, create_engine

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("RELIABASE_DB", "./reliabase.sqlite")).resolve()


def _current_db_url() -> str:
    """Compute the active database URL from environment (avoids stale globals)."""
    return os.getenv("RELIABASE_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")


def _current_echo() -> bool:
    return os.getenv("RELIABASE_ECHO_SQL", "false").lower() == "true"


def get_engine(database_url: str | None = None):
    """Return a SQLModel engine configured from env or an override URL."""
    db_url = database_url or _current_db_url()
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, echo=_current_echo(), connect_args=connect_args, poolclass=NullPool)


def init_db(engine=None, database_url: str | None = None) -> None:
    """Create database tables if they do not exist."""
    engine = engine or get_engine(database_url)
    SQLModel.metadata.create_all(engine)
