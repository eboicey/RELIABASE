"""Configuration helpers for RELIABASE.

Reads environment variables for database path and app settings. Defaults to a local
SQLite file for a local-first workflow.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("RELIABASE_DB", "./reliabase.sqlite")).resolve()
DATABASE_URL = os.getenv("RELIABASE_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
ECHO_SQL = os.getenv("RELIABASE_ECHO_SQL", "false").lower() == "true"


def get_engine():
    """Return a SQLModel engine configured for SQLite by default."""
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    return create_engine(DATABASE_URL, echo=ECHO_SQL, connect_args=connect_args)


def init_db(engine=None) -> None:
    """Create database tables if they do not exist."""
    engine = engine or get_engine()
    SQLModel.metadata.create_all(engine)
