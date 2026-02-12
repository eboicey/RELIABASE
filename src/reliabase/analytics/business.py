"""Business impact and decision-support metrics.

Connects reliability/manufacturing data to financial and operational
decision making: cost of unreliability, PM optimisation, spare-parts
demand forecasting, and a composite asset health index.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import gamma
from typing import Sequence

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Cost of Unreliability (COUR)
# ---------------------------------------------------------------------------

@dataclass
class COURResult:
    """Estimated financial impact of unplanned downtime."""
    total_cost: float                 # currency units (user-configured)
    lost_production_cost: float       # downtime × hourly production value
    repair_cost: float                # failure count × average repair cost
    unplanned_downtime_hours: float
    failure_count: int
    cost_per_failure: float


def compute_cour(
    unplanned_downtime_hours: float,
    failure_count: int,
    hourly_production_value: float = 500.0,
    avg_repair_cost: float = 1500.0,
) -> COURResult:
    """Estimate Cost Of Unreliability.

    COUR = (unplanned downtime × $/hr production loss) + (failures × avg repair cost)

    Default values represent typical mid-range industrial equipment.
    Users should configure these per-asset or per-plant.
    """
    lost_prod = unplanned_downtime_hours * hourly_production_value
    repair = failure_count * avg_repair_cost
    total = lost_prod + repair
    cost_per = total / failure_count if failure_count > 0 else 0.0
    return COURResult(
        total_cost=round(total, 2),
        lost_production_cost=round(lost_prod, 2),
        repair_cost=round(repair, 2),
        unplanned_downtime_hours=round(unplanned_downtime_hours, 2),
        failure_count=failure_count,
        cost_per_failure=round(cost_per, 2),
    )


# ---------------------------------------------------------------------------
# PM Optimisation Score
# ---------------------------------------------------------------------------

@dataclass
class PMOptimizationResult:
    """Evaluates whether current PM frequency is appropriate given failure behaviour.

    Interpretation of the Weibull shape (β):
      β < 1  → infant mortality (PM may be counter-productive)
      β ≈ 1  → random failures (PM has limited value; condition monitoring preferred)
      β > 1  → wear-out (PM is beneficial; schedule based on B-life)

    The pm_ratio compares current PM interval to the recommended B10 life.
      ratio < 0.8 → over-maintaining (too frequent)
      0.8 ≤ ratio ≤ 1.2 → appropriately scheduled
      ratio > 1.2 → under-maintaining (too infrequent, risk of failures)
    """
    weibull_shape: float
    failure_pattern: str       # 'infant_mortality' | 'random' | 'wearout'
    recommended_pm_hours: float  # B10 life as a starting point
    current_pm_hours: float | None
    pm_ratio: float | None      # current / recommended
    assessment: str            # 'over_maintaining' | 'appropriate' | 'under_maintaining' | 'pm_not_recommended'


def compute_pm_optimization(
    shape: float,
    scale: float,
    current_pm_interval_hours: float | None = None,
    target_percentile: float = 10.0,
) -> PMOptimizationResult:
    """Evaluate PM scheduling effectiveness using Weibull parameters.

    Recommends PM interval based on Bx life (default B10).
    """
    # Failure pattern classification
    if shape < 0.95:
        pattern = "infant_mortality"
    elif shape <= 1.05:
        pattern = "random"
    else:
        pattern = "wearout"

    # Recommended PM at target_percentile (B10 by default)
    p = target_percentile / 100.0
    recommended = scale * (-np.log(1 - p)) ** (1.0 / shape)

    pm_ratio = None
    if current_pm_interval_hours and current_pm_interval_hours > 0:
        pm_ratio = current_pm_interval_hours / recommended if recommended > 0 else None

    # Assessment
    if pattern == "infant_mortality":
        assessment = "pm_not_recommended"
    elif pattern == "random":
        assessment = "pm_not_recommended"
    elif pm_ratio is None:
        assessment = "no_pm_data"
    elif pm_ratio < 0.8:
        assessment = "over_maintaining"
    elif pm_ratio <= 1.2:
        assessment = "appropriate"
    else:
        assessment = "under_maintaining"

    return PMOptimizationResult(
        weibull_shape=round(shape, 4),
        failure_pattern=pattern,
        recommended_pm_hours=round(float(recommended), 2),
        current_pm_hours=current_pm_interval_hours,
        pm_ratio=round(pm_ratio, 4) if pm_ratio is not None else None,
        assessment=assessment,
    )


# ---------------------------------------------------------------------------
# Spare Parts Demand Forecast
# ---------------------------------------------------------------------------

@dataclass
class SparePartForecast:
    """Predicted part consumption over a planning horizon."""
    part_name: str
    expected_failures: float
    lower_bound: float      # 5th percentile
    upper_bound: float      # 95th percentile


@dataclass
class SpareDemandResult:
    """Fleet-level spare parts demand forecast."""
    horizon_hours: float
    forecasts: list[SparePartForecast] = field(default_factory=list)
    total_expected_failures: float = 0.0


def forecast_spare_demand(
    part_failure_data: Sequence[dict],
    horizon_hours: float = 8760.0,  # 1 year default
) -> SpareDemandResult:
    """Forecast spare part demand using Poisson assumption from historical failure rates.

    Parameters
    ----------
    part_failure_data : list of dicts with keys:
        part_name, failure_rate_per_hour (λ), current_stock (optional)
    horizon_hours : planning window in hours (default 8760 = 1 year)
    """
    forecasts: list[SparePartForecast] = []
    total_expected = 0.0

    for d in part_failure_data:
        lam = d["failure_rate_per_hour"] * horizon_hours
        lower = float(stats.poisson.ppf(0.05, lam)) if lam > 0 else 0.0
        upper = float(stats.poisson.ppf(0.95, lam)) if lam > 0 else 0.0
        forecasts.append(SparePartForecast(
            part_name=d["part_name"],
            expected_failures=round(lam, 2),
            lower_bound=lower,
            upper_bound=upper,
        ))
        total_expected += lam

    return SpareDemandResult(
        horizon_hours=horizon_hours,
        forecasts=forecasts,
        total_expected_failures=round(total_expected, 2),
    )


# ---------------------------------------------------------------------------
# Asset Health Index (AHI)
# ---------------------------------------------------------------------------

@dataclass
class AssetHealthIndex:
    """Composite 0-100 health score for an asset.

    Combines reliability, operational, and maintenance signals into
    a single actionable indicator.
    """
    score: float               # 0 (worst) to 100 (best)
    grade: str                 # A / B / C / D / F
    components: dict           # individual sub-scores

    # Thresholds: A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, F < 40


def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    return "F"


def compute_health_index(
    availability: float,
    mtbf_hours: float,
    mtbf_target_hours: float | None = None,
    unplanned_ratio: float = 0.0,
    weibull_shape: float | None = None,
    oee: float | None = None,
    repair_trend_ratio: float = 1.0,
) -> AssetHealthIndex:
    """Compute a composite Asset Health Index (0-100).

    Sub-scores (each 0-100, weighted):
      - Availability score (weight 0.30): availability × 100
      - MTBF score (weight 0.25): min(mtbf / target, 1) × 100
      - Downtime quality (weight 0.15): (1 - unplanned_ratio) × 100
      - Wear-out margin (weight 0.15): β > 1 reduces score proportionally
      - OEE score (weight 0.10): oee × 100
      - Repair trend (weight 0.05): based on repair effectiveness ratio

    Parameters
    ----------
    mtbf_target_hours : expected MTBF for this asset class. None = use mtbf × 1.2.
    """
    if mtbf_target_hours is None:
        mtbf_target_hours = mtbf_hours * 1.2 if mtbf_hours > 0 else 1.0

    # Individual component scores (0-100)
    avail_score = min(availability, 1.0) * 100

    mtbf_ratio = mtbf_hours / mtbf_target_hours if mtbf_target_hours > 0 else 0.0
    mtbf_score = min(mtbf_ratio, 1.0) * 100

    dt_quality_score = (1.0 - min(unplanned_ratio, 1.0)) * 100

    # Wear-out margin: β near 1 is neutral, β >> 1 means aggressive wear
    if weibull_shape is not None and weibull_shape > 0:
        if weibull_shape < 1.0:
            wearout_score = 70.0  # infant mortality — concerning but different
        elif weibull_shape <= 1.5:
            wearout_score = 90.0  # mild wear-out
        elif weibull_shape <= 2.5:
            wearout_score = 70.0  # moderate wear-out
        else:
            wearout_score = 50.0  # aggressive wear-out
    else:
        wearout_score = 75.0  # unknown — neutral

    oee_score = min(oee, 1.0) * 100 if oee is not None else 75.0

    # Repair trend: ratio ~1 is neutral, <1 improving, >1 degrading
    if repair_trend_ratio >= 1.0:
        repair_score = max(0, 100 - (repair_trend_ratio - 1.0) * 50)
    else:
        repair_score = min(100, 100 + (1.0 - repair_trend_ratio) * 20)

    components = {
        "availability": round(avail_score, 1),
        "mtbf_performance": round(mtbf_score, 1),
        "downtime_quality": round(dt_quality_score, 1),
        "wearout_margin": round(wearout_score, 1),
        "oee": round(oee_score, 1),
        "repair_trend": round(repair_score, 1),
    }

    # Weighted composite
    weights = {
        "availability": 0.30,
        "mtbf_performance": 0.25,
        "downtime_quality": 0.15,
        "wearout_margin": 0.15,
        "oee": 0.10,
        "repair_trend": 0.05,
    }
    score = sum(components[k] * weights[k] for k in weights)
    score = round(max(0, min(100, score)), 1)

    return AssetHealthIndex(score=score, grade=_grade(score), components=components)
