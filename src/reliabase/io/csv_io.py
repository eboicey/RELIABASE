"""CSV import/export helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Type

import pandas as pd
from sqlmodel import Session, SQLModel, select


def export_to_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def import_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def export_records(records: Iterable[dict], path: Path) -> Path:
    df = pd.DataFrame(records)
    return export_to_csv(df, path)


def export_table(session: Session, model: Type[SQLModel], path: Path) -> Path:
    rows = session.exec(select(model)).all()
    records = [row.dict() for row in rows]
    return export_records(records, path)


def import_table(session: Session, model: Type[SQLModel], path: Path) -> int:
    df = import_csv(path)
    count = 0
    for row in df.to_dict(orient="records"):
        obj = model(**row)
        session.add(obj)
        count += 1
    session.commit()
    return count
