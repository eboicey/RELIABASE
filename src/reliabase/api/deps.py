"""FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated, Iterator

from fastapi import Depends
from sqlmodel import Session

from reliabase.database import get_session


def get_db_session() -> Iterator[Session]:
    with get_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db_session)]
