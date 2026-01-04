"""Reliability KPI computations (MTBF, MTTR, availability)."""
from __future__ import annotations

from typing import Iterable


def compute_mtbf(time_between_failures: Iterable[float]) -> float:
    """Compute mean time between failures.

    Expects time-between-failure intervals (e.g., hours) already derived from exposure logs.
    """
    data = list(time_between_failures)
    if not data:
        return 0.0
    return sum(data) / len(data)


def compute_mttr(downtime_minutes: Iterable[float]) -> float:
    """Compute mean time to repair from downtime durations in minutes."""
    data = [d for d in downtime_minutes if d is not None]
    if not data:
        return 0.0
    return sum(data) / len(data)


def compute_availability(mtbf_hours: float, mttr_hours: float) -> float:
    """Availability defined as MTBF / (MTBF + MTTR).

    Assumes MTBF and MTTR expressed in the same units (hours recommended).
    """
    denominator = mtbf_hours + mttr_hours
    if denominator <= 0:
        return 0.0
    return mtbf_hours / denominator
