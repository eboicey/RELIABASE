"""Extended reliability metrics beyond core MTBF/MTTR/Availability.

Includes B-life, failure rate, conditional reliability, bad-actor ranking,
repair effectiveness, and Risk Priority Number (RPN).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

import numpy as np
from scipy import stats

from reliabase.models import Event, EventFailureDetail, ExposureLog


# ---------------------------------------------------------------------------
# B-Life (Bx Life)
# ---------------------------------------------------------------------------

@dataclass
class BLifeResult:
    """Bx Life — time at which x% of the population is expected to fail."""
    percentile: float          # e.g. 10 for B10
    life_hours: float          # hours at which x% have failed
    shape: float
    scale: float


def compute_b_life(shape: float, scale: float, percentile: float = 10.0) -> BLifeResult:
    """Compute Bx life from Weibull shape/scale.

    B10 = time at which 10 % of assets have failed.
    Uses the Weibull quantile function: t = scale * (-ln(1 - p))^(1/shape).
    """
    if percentile <= 0 or percentile >= 100:
        raise ValueError("percentile must be in (0, 100)")
    p = percentile / 100.0
    life = scale * (-np.log(1 - p)) ** (1.0 / shape)
    return BLifeResult(percentile=percentile, life_hours=round(float(life), 2), shape=shape, scale=scale)


# ---------------------------------------------------------------------------
# Failure Rate
# ---------------------------------------------------------------------------

@dataclass
class FailureRateResult:
    """Average and instantaneous failure rates."""
    average_rate: float        # failures per hour over observation window
    instantaneous_rate: float  # Weibull hazard at latest operating age
    total_failures: int
    total_hours: float


def compute_failure_rate(
    total_failures: int,
    total_operating_hours: float,
    shape: float | None = None,
    scale: float | None = None,
    current_age_hours: float | None = None,
) -> FailureRateResult:
    """Compute average failure rate (λ = failures / hours) and Weibull instantaneous hazard.

    Instantaneous rate uses h(t) = (shape/scale) * (t/scale)^(shape-1).
    """
    avg_rate = total_failures / total_operating_hours if total_operating_hours > 0 else 0.0
    instant_rate = 0.0
    if shape and scale and current_age_hours and current_age_hours > 0:
        instant_rate = (shape / scale) * ((current_age_hours / scale) ** (shape - 1))
    return FailureRateResult(
        average_rate=round(avg_rate, 6),
        instantaneous_rate=round(float(instant_rate), 6),
        total_failures=total_failures,
        total_hours=round(total_operating_hours, 2),
    )


# ---------------------------------------------------------------------------
# Conditional Reliability
# ---------------------------------------------------------------------------

@dataclass
class ConditionalReliabilityResult:
    """Probability of surviving an additional delta_t given survival to age t."""
    current_age: float
    mission_time: float
    conditional_reliability: float


def compute_conditional_reliability(
    shape: float, scale: float, current_age: float, mission_time: float
) -> ConditionalReliabilityResult:
    """R(t + Δt | T > t) = R(t + Δt) / R(t).

    Key for mission planning: "If this asset has already run 500 h,
    what is the probability it will survive another 100 h?"
    """
    dist = stats.weibull_min(c=shape, scale=scale)
    r_t = dist.sf(current_age)
    r_total = dist.sf(current_age + mission_time)
    cond_r = r_total / r_t if r_t > 1e-12 else 0.0
    return ConditionalReliabilityResult(
        current_age=current_age,
        mission_time=mission_time,
        conditional_reliability=round(float(cond_r), 6),
    )


# ---------------------------------------------------------------------------
# MTTF (Mean Time To Failure — for non-repairable items)
# ---------------------------------------------------------------------------

def compute_mttf(shape: float, scale: float) -> float:
    """MTTF from Weibull parameters: scale * Γ(1 + 1/shape)."""
    from math import gamma
    return round(scale * gamma(1 + 1.0 / shape), 2)


# ---------------------------------------------------------------------------
# Repair Effectiveness
# ---------------------------------------------------------------------------

@dataclass
class RepairEffectivenessResult:
    """Measures whether repairs restore the asset to good-as-new.

    A trend ratio > 1 indicates improving intervals (later TBFs are longer).
    A trend ratio < 1 indicates degrading intervals (later TBFs are shorter).
    A trend ratio ≈ 1 indicates as-good-as-old (minimal repair model).
    """
    trend_ratio: float         # ratio of median of later half vs. earlier half
    intervals_count: int
    improving: bool


def compute_repair_effectiveness(intervals: Sequence[float]) -> RepairEffectivenessResult:
    """Evaluate repair effectiveness by comparing first-half vs. second-half TBF intervals.

    Simple split-half approach: if later intervals are shorter, repairs are not
    restoring the asset to like-new condition.
    """
    arr = np.array(list(intervals), dtype=float)
    arr = arr[arr > 0]
    if arr.size < 4:
        return RepairEffectivenessResult(trend_ratio=1.0, intervals_count=int(arr.size), improving=True)
    mid = arr.size // 2
    first_half = np.median(arr[:mid])
    second_half = np.median(arr[mid:])
    ratio = second_half / first_half if first_half > 1e-12 else 1.0
    return RepairEffectivenessResult(
        trend_ratio=round(float(ratio), 4),
        intervals_count=int(arr.size),
        improving=bool(ratio >= 1.0),
    )


# ---------------------------------------------------------------------------
# Bad Actor Analysis
# ---------------------------------------------------------------------------

@dataclass
class BadActorEntry:
    """One row of the bad-actor ranking table."""
    asset_id: int
    asset_name: str
    failure_count: int
    total_downtime_hours: float
    availability: float
    composite_score: float     # higher = worse performer


@dataclass
class BadActorAnalysis:
    """Fleet-level ranking of worst-performing assets."""
    entries: list[BadActorEntry] = field(default_factory=list)


def rank_bad_actors(
    asset_data: Sequence[dict],
    top_n: int = 10,
) -> BadActorAnalysis:
    """Rank assets by a composite "bad actor" score.

    composite_score = (failure_count * w_f) + (downtime_hours * w_d) + ((1 - availability) * w_a)
    Weights emphasize failure count and downtime impact.

    Parameters
    ----------
    asset_data : list of dicts with keys:
        asset_id, asset_name, failure_count, total_downtime_hours, availability
    """
    w_f, w_d, w_a = 0.4, 0.35, 0.25

    # Normalise each dimension to [0, 1] using max values
    if not asset_data:
        return BadActorAnalysis()

    max_failures = max(d["failure_count"] for d in asset_data) or 1
    max_downtime = max(d["total_downtime_hours"] for d in asset_data) or 1.0

    entries: list[BadActorEntry] = []
    for d in asset_data:
        norm_f = d["failure_count"] / max_failures
        norm_d = d["total_downtime_hours"] / max_downtime
        norm_a = 1.0 - d["availability"]  # already 0..1
        score = w_f * norm_f + w_d * norm_d + w_a * norm_a
        entries.append(
            BadActorEntry(
                asset_id=d["asset_id"],
                asset_name=d["asset_name"],
                failure_count=d["failure_count"],
                total_downtime_hours=d["total_downtime_hours"],
                availability=d["availability"],
                composite_score=round(score, 4),
            )
        )
    entries.sort(key=lambda e: e.composite_score, reverse=True)
    return BadActorAnalysis(entries=entries[:top_n])


# ---------------------------------------------------------------------------
# Risk Priority Number (RPN)
# ---------------------------------------------------------------------------

@dataclass
class RPNEntry:
    """RPN for a single failure mode."""
    failure_mode: str
    severity: int          # 1-10
    occurrence: int        # 1-10
    detection: int         # 1-10
    rpn: int               # severity * occurrence * detection


@dataclass
class RPNAnalysis:
    """FMEA-style RPN ranking."""
    entries: list[RPNEntry] = field(default_factory=list)
    max_rpn: int = 0


def compute_rpn(
    failure_mode_data: Sequence[dict],
    total_events: int,
) -> RPNAnalysis:
    """Compute Risk Priority Number for each failure mode.

    Occurrence (1-10) is derived from failure count relative to total events.
    Severity (1-10) is derived from average downtime of that failure mode.
    Detection (1-10) defaults to 5 (moderate) since we don't have inspection data granularity yet.

    Parameters
    ----------
    failure_mode_data : list of dicts with keys:
        name, count, avg_downtime_minutes
    total_events : total event count across all modes (for occurrence scaling)
    """
    if not failure_mode_data or total_events <= 0:
        return RPNAnalysis()

    max_dt = max(d.get("avg_downtime_minutes", 0) for d in failure_mode_data) or 1.0

    entries: list[RPNEntry] = []
    for d in failure_mode_data:
        # Occurrence: proportional frequency scaled to 1-10
        occ_frac = d["count"] / total_events
        occurrence = max(1, min(10, int(np.ceil(occ_frac * 10))))

        # Severity: proportional to average downtime scaled to 1-10
        sev_frac = d.get("avg_downtime_minutes", 0) / max_dt
        severity = max(1, min(10, int(np.ceil(sev_frac * 10))))

        # Detection: default moderate (can be refined with inspection coverage later)
        detection = d.get("detection", 5)

        rpn = severity * occurrence * detection
        entries.append(RPNEntry(
            failure_mode=d["name"],
            severity=severity,
            occurrence=occurrence,
            detection=detection,
            rpn=rpn,
        ))

    entries.sort(key=lambda e: e.rpn, reverse=True)
    max_rpn = entries[0].rpn if entries else 0
    return RPNAnalysis(entries=entries, max_rpn=max_rpn)
