"""CSV import/export stubs."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


def export_to_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def import_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def export_records(records: Iterable[dict], path: Path) -> Path:
    df = pd.DataFrame(records)
    return export_to_csv(df, path)
