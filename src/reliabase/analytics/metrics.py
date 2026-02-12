"""Reliability KPI computations (MTBF, MTTR, availability)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence

from reliabase.models import Event, ExposureLog


@dataclass
class TbfResult:
    intervals_hours: list[float]
    censored_flags: list[bool]


@dataclass
class FleetKPI:
    """Typed container for aggregate KPI results.

    Supports dict-style access (``kpi["mtbf_hours"]``, ``"key" in kpi``)
    for backward compatibility with code that treated the old plain-dict return.
    """
    mtbf_hours: float = 0.0
    mttr_hours: float = 0.0
    availability: float = 0.0
    intervals_hours: list[float] | None = None
    censored_flags: list[bool] | None = None
    failure_rate: float = 0.0
    total_exposure_hours: float = 0.0
    failure_count: int = 0
    total_events: int = 0

    _FIELDS: frozenset[str] = frozenset({
        "mtbf_hours", "mttr_hours", "availability", "intervals_hours",
        "censored_flags", "failure_rate", "total_exposure_hours",
        "failure_count", "total_events",
    })

    def __post_init__(self) -> None:
        if self.intervals_hours is None:
            self.intervals_hours = []
        if self.censored_flags is None:
            self.censored_flags = []

    # -- dict-like helpers for backward compatibility -------------------------
    def __getitem__(self, key: str) -> object:
        if key in self._FIELDS:
            return getattr(self, key)
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        return key in self._FIELDS

    def get(self, key: str, default: object = None) -> object:
        """Dict-style ``.get()`` for backward compatibility."""
        if key in self._FIELDS:
            return getattr(self, key)
        return default


def compute_mtbf(time_between_failures: Iterable[float]) -> float:
    """Compute mean time between failures.

    Expects time-between-failure intervals (e.g., hours) already derived from exposure logs.
    """
    data = [d for d in time_between_failures if d is not None]
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


def _overlap_hours(log: ExposureLog, start: datetime, end: datetime) -> float:
    """Estimate uptime hours contributed by a log overlapping [start, end]."""
    window_start = max(log.start_time, start)
    window_end = min(log.end_time, end)
    if window_end <= window_start:
        return 0.0
    total_seconds = (log.end_time - log.start_time).total_seconds()
    overlap_seconds = (window_end - window_start).total_seconds()
    if total_seconds <= 0:
        return 0.0
    proportion = overlap_seconds / total_seconds
    base_hours = log.hours if log.hours and log.hours > 0 else total_seconds / 3600
    return base_hours * proportion


def _uptime_between(exposures: Sequence[ExposureLog], start: datetime, end: datetime) -> float:
    return sum(_overlap_hours(log, start, end) for log in exposures)


def derive_time_between_failures(exposures: Sequence[ExposureLog], failure_events: Sequence[Event]) -> TbfResult:
    """Derive time-between-failure intervals using exposure logs and failure timestamps.

    Handles right-censoring by appending a censored interval from last failure to
    last exposure end when no subsequent failure exists.
    """
    exposures_sorted = sorted(exposures, key=lambda x: x.start_time)
    failures_sorted = sorted(failure_events, key=lambda x: x.timestamp)
    if not exposures_sorted or not failures_sorted:
        return TbfResult(intervals_hours=[], censored_flags=[])

    intervals: list[float] = []
    censored: list[bool] = []

    first_exposure_start = exposures_sorted[0].start_time
    previous_time = first_exposure_start

    for failure in failures_sorted:
        interval_hours = _uptime_between(exposures_sorted, previous_time, failure.timestamp)
        intervals.append(interval_hours)
        censored.append(False)
        previous_time = failure.timestamp

    last_exposure_end = exposures_sorted[-1].end_time
    if last_exposure_end > previous_time:
        censored_interval = _uptime_between(exposures_sorted, previous_time, last_exposure_end)
        intervals.append(censored_interval)
        censored.append(True)

    return TbfResult(intervals_hours=intervals, censored_flags=censored)


def compute_failure_rate_simple(failures: int, total_hours: float) -> float:
    """Simple average failure rate: λ = failures / total operating hours."""
    return failures / total_hours if total_hours > 0 else 0.0


def aggregate_kpis(exposures: Sequence[ExposureLog], events: Sequence[Event]) -> FleetKPI:
    """Compute MTBF/MTTR/availability and extended metrics based on exposure logs and events.

    - MTBF uses time-between-failure intervals derived from exposure logs.
    - MTTR uses downtime_minutes on failure events (converted to hours).
    - Failure rate, total exposure hours, and event counts included for downstream use.
    """
    failure_events = [e for e in events if e.event_type and e.event_type.lower() == "failure"]
    tbf = derive_time_between_failures(exposures, failure_events)
    mtbf_hours = compute_mtbf(tbf.intervals_hours)
    mttr_hours = compute_mttr([e.downtime_minutes for e in failure_events]) / 60 if failure_events else 0.0
    availability = compute_availability(mtbf_hours, mttr_hours)
    total_hours = sum(e.hours for e in exposures if e.hours and e.hours > 0)
    failure_rate = compute_failure_rate_simple(len(failure_events), total_hours)
    return FleetKPI(
        mtbf_hours=round(mtbf_hours, 2),
        mttr_hours=round(mttr_hours, 2),
        availability=round(availability, 4),
        intervals_hours=tbf.intervals_hours,
        censored_flags=tbf.censored_flags,
        failure_rate=round(failure_rate, 6),
        total_exposure_hours=round(total_hours, 2),
        failure_count=len(failure_events),
        total_events=len(events),
    )
