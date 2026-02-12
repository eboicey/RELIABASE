"""Manufacturing performance metrics — OEE framework and related KPIs.

Bridges reliability data to manufacturing performance by computing
OEE (Overall Equipment Effectiveness), performance rate, quality rate,
planned/unplanned downtime split, and MTBM.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np

from reliabase.models import Event, ExposureLog


# ---------------------------------------------------------------------------
# OEE — Overall Equipment Effectiveness
# ---------------------------------------------------------------------------

@dataclass
class OEEResult:
    """OEE = Availability × Performance × Quality, each 0..1."""
    availability: float
    performance: float
    quality: float
    oee: float


def compute_oee(
    availability: float,
    performance: float = 1.0,
    quality: float = 1.0,
) -> OEEResult:
    """Calculate Overall Equipment Effectiveness.

    Availability is sourced from reliability KPIs (MTBF / (MTBF + MTTR)).
    Performance is actual throughput / design throughput (default 1.0 if unknown).
    Quality is good units / total units (default 1.0 if no rejection data).

    These defaults are conservative — as the system collects more operational
    data the inputs will become more precise.
    """
    oee = availability * performance * quality
    return OEEResult(
        availability=round(availability, 4),
        performance=round(performance, 4),
        quality=round(quality, 4),
        oee=round(oee, 4),
    )


# ---------------------------------------------------------------------------
# Performance Rate
# ---------------------------------------------------------------------------

@dataclass
class PerformanceRateResult:
    """Actual vs. design capacity utilisation."""
    actual_throughput: float    # units (cycles) per operating hour
    design_throughput: float    # expected units per hour at full rate
    performance_rate: float    # actual / design  (0..1+)
    total_cycles: float
    total_operating_hours: float


def compute_performance_rate(
    exposures: Sequence[ExposureLog],
    design_cycles_per_hour: float | None = None,
) -> PerformanceRateResult:
    """Derive performance rate from exposure logs.

    Uses cycles and hours from exposure records.  If design_cycles_per_hour
    is not provided, estimates it from the single best-performing shift
    (max cycles/hour in any single exposure record).
    """
    total_cycles = sum(e.cycles for e in exposures if e.cycles)
    total_hours = sum(e.hours for e in exposures if e.hours and e.hours > 0)

    actual_throughput = total_cycles / total_hours if total_hours > 0 else 0.0

    # Estimate design throughput from best observed rate if not given
    if design_cycles_per_hour is None:
        rates = [
            e.cycles / e.hours
            for e in exposures
            if e.hours and e.hours > 0 and e.cycles and e.cycles > 0
        ]
        design_cycles_per_hour = max(rates) if rates else actual_throughput or 1.0

    perf_rate = actual_throughput / design_cycles_per_hour if design_cycles_per_hour > 0 else 0.0

    return PerformanceRateResult(
        actual_throughput=round(actual_throughput, 4),
        design_throughput=round(design_cycles_per_hour, 4),
        performance_rate=round(min(perf_rate, 1.0), 4),  # cap at 1.0
        total_cycles=total_cycles,
        total_operating_hours=round(total_hours, 2),
    )


# ---------------------------------------------------------------------------
# Planned vs Unplanned Downtime
# ---------------------------------------------------------------------------

@dataclass
class DowntimeSplitResult:
    """Breakdown of downtime into planned and unplanned categories."""
    planned_downtime_hours: float
    unplanned_downtime_hours: float
    total_downtime_hours: float
    unplanned_ratio: float     # fraction of downtime that is unplanned
    planned_count: int
    unplanned_count: int


def compute_downtime_split(events: Sequence[Event]) -> DowntimeSplitResult:
    """Split total downtime into planned (maintenance/inspection) vs unplanned (failure).

    Uses the event_type field:
      - 'failure' -> unplanned
      - 'maintenance', 'inspection' -> planned
    """
    planned_mins = 0.0
    unplanned_mins = 0.0
    planned_count = 0
    unplanned_count = 0

    for e in events:
        dt = e.downtime_minutes or 0.0
        etype = (e.event_type or "").lower()
        if etype == "failure":
            unplanned_mins += dt
            unplanned_count += 1
        else:
            planned_mins += dt
            planned_count += 1

    planned_hrs = planned_mins / 60.0
    unplanned_hrs = unplanned_mins / 60.0
    total = planned_hrs + unplanned_hrs
    ratio = unplanned_hrs / total if total > 0 else 0.0

    return DowntimeSplitResult(
        planned_downtime_hours=round(planned_hrs, 2),
        unplanned_downtime_hours=round(unplanned_hrs, 2),
        total_downtime_hours=round(total, 2),
        unplanned_ratio=round(ratio, 4),
        planned_count=planned_count,
        unplanned_count=unplanned_count,
    )


# ---------------------------------------------------------------------------
# MTBM — Mean Time Between Maintenance (all types)
# ---------------------------------------------------------------------------

@dataclass
class MTBMResult:
    """Mean Time Between Maintenance — uses all event types, not just failures."""
    mtbm_hours: float
    maintenance_events: int
    total_operating_hours: float


def compute_mtbm(
    exposures: Sequence[ExposureLog],
    events: Sequence[Event],
) -> MTBMResult:
    """MTBM = total operating hours / number of maintenance-related events.

    Includes failures, scheduled maintenance, and inspections — any event
    that takes the equipment out of service.
    """
    total_hours = sum(e.hours for e in exposures if e.hours and e.hours > 0)
    maint_events = [e for e in events if (e.downtime_minutes or 0) > 0]
    count = len(maint_events)
    mtbm = total_hours / count if count > 0 else total_hours
    return MTBMResult(
        mtbm_hours=round(mtbm, 2),
        maintenance_events=count,
        total_operating_hours=round(total_hours, 2),
    )


# ---------------------------------------------------------------------------
# Aggregate manufacturing KPIs
# ---------------------------------------------------------------------------

@dataclass
class ManufacturingKPIs:
    """Consolidated manufacturing metrics for one asset."""
    oee: OEEResult
    performance: PerformanceRateResult
    downtime_split: DowntimeSplitResult
    mtbm: MTBMResult


def aggregate_manufacturing_kpis(
    exposures: Sequence[ExposureLog],
    events: Sequence[Event],
    availability: float,
    design_cycles_per_hour: float | None = None,
    quality_rate: float = 1.0,
) -> ManufacturingKPIs:
    """One-call computation of all manufacturing metrics for an asset.

    Parameters
    ----------
    availability : reliability-based availability (MTBF/(MTBF+MTTR))
    design_cycles_per_hour : nominal throughput. None = auto-estimate.
    quality_rate : fraction of output meeting spec (default 1.0).
    """
    perf = compute_performance_rate(exposures, design_cycles_per_hour)
    oee = compute_oee(availability, perf.performance_rate, quality_rate)
    dt_split = compute_downtime_split(events)
    mtbm = compute_mtbm(exposures, events)
    return ManufacturingKPIs(oee=oee, performance=perf, downtime_split=dt_split, mtbm=mtbm)
