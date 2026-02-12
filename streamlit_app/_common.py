"""Shared bootstrap for all RELIABASE Streamlit pages.

Import this module at the top of every page (after ``st.set_page_config``)
to configure ``sys.path``, initialise the database, and obtain sessions.

Usage::

    import streamlit as st
    st.set_page_config(...)

    from _common import get_session   # noqa: E402  (must come after set_page_config)
    # … then use ``with get_session() as session:``
"""
from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import streamlit as st
from sqlmodel import Session

log = logging.getLogger("reliabase.ui")

# ── path setup ────────────────────────────────────────────────────────────
_SRC_PATH = str((Path(__file__).parent.parent / "src").resolve())
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

# ── lazy imports (only available after path is set) ───────────────────────
from reliabase.config import get_engine, init_db, DEFAULT_DB_PATH  # noqa: E402

log.info("RELIABASE database path: %s", DEFAULT_DB_PATH)

# Ensure tables exist on first import.
init_db()


# ── session helper ────────────────────────────────────────────────────────
@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a :class:`sqlmodel.Session` using the cached engine.

    Mirrors :func:`reliabase.database.get_session` so all Streamlit pages
    share the same engine/pool without each page re-creating its own.
    """
    engine = get_engine()
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def handle_error(exc: Exception, *, context: str = "operation") -> None:
    """Display a user-friendly error toast and log the traceback."""
    log.exception("Error during %s", context)
    st.error(f"Something went wrong during {context}. Details: {exc}")
