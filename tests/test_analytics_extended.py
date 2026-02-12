"""Tests for expanded analytics: reliability_extended, manufacturing, business."""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from reliabase.analytics import reliability_extended, manufacturing, business, metrics
from reliabase.models import Event, ExposureLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exposure(start: datetime, hours: float, cycles: float = 0.0) -> ExposureLog:
    return ExposureLog(
        asset_id=1, start_time=start,
        end_time=start + timedelta(hours=hours),
        hours=hours, cycles=cycles,
    )


def _make_event(ts: datetime, etype: str = "failure", downtime: float = 60.0) -> Event:
    return Event(asset_id=1, timestamp=ts, event_type=etype, downtime_minutes=downtime)


# =========================================================================
# reliability_extended
# =========================================================================

class TestBLife:
    def test_b10_basic(self):
        result = reliability_extended.compute_b_life(shape=2.0, scale=1000.0, percentile=10.0)
        assert result.percentile == 10.0
        assert result.life_hours > 0
        assert result.life_hours < 1000.0  # B10 < characteristic life

    def test_b50_equals_median(self):
        # B50 should equal the Weibull median: scale * (ln2)^(1/shape)
        result = reliability_extended.compute_b_life(shape=2.0, scale=1000.0, percentile=50.0)
        expected_median = 1000.0 * (np.log(2)) ** 0.5
        assert abs(result.life_hours - expected_median) < 0.01

    def test_invalid_percentile(self):
        with pytest.raises(ValueError):
            reliability_extended.compute_b_life(2.0, 1000.0, 0.0)
        with pytest.raises(ValueError):
            reliability_extended.compute_b_life(2.0, 1000.0, 100.0)


class TestFailureRate:
    def test_average_rate(self):
        result = reliability_extended.compute_failure_rate(5, 1000.0)
        assert abs(result.average_rate - 0.005) < 1e-9

    def test_with_weibull_instantaneous(self):
        result = reliability_extended.compute_failure_rate(
            5, 1000.0, shape=2.0, scale=500.0, current_age_hours=400.0,
        )
        assert result.instantaneous_rate > 0
        assert result.average_rate == pytest.approx(0.005)

    def test_zero_hours(self):
        result = reliability_extended.compute_failure_rate(3, 0.0)
        assert result.average_rate == 0.0


class TestConditionalReliability:
    def test_young_asset_high_reliability(self):
        # A young asset with wearout (β>1) should have high conditional R
        cr = reliability_extended.compute_conditional_reliability(
            shape=2.0, scale=1000.0, current_age=100.0, mission_time=50.0,
        )
        assert cr.conditional_reliability > 0.9

    def test_old_asset_lower_reliability(self):
        cr = reliability_extended.compute_conditional_reliability(
            shape=2.0, scale=1000.0, current_age=900.0, mission_time=200.0,
        )
        # At age 900 with scale 1000, conditional R for 200h mission is lower than young asset
        assert cr.conditional_reliability < 0.9


class TestMTTF:
    def test_mttf_basic(self):
        mttf = reliability_extended.compute_mttf(shape=2.0, scale=1000.0)
        # MTTF = scale * Γ(1 + 1/shape) = 1000 * Γ(1.5) ≈ 886.23
        assert abs(mttf - 886.23) < 1.0


class TestRepairEffectiveness:
    def test_improving(self):
        # Later intervals longer → improving
        intervals = [50, 60, 70, 80, 90, 100]
        re = reliability_extended.compute_repair_effectiveness(intervals)
        assert re.improving is True
        assert re.trend_ratio >= 1.0

    def test_degrading(self):
        # Later intervals shorter → degrading
        intervals = [100, 90, 80, 70, 60, 50]
        re = reliability_extended.compute_repair_effectiveness(intervals)
        assert re.improving is False
        assert re.trend_ratio < 1.0

    def test_insufficient_data(self):
        re = reliability_extended.compute_repair_effectiveness([100, 200])
        assert re.trend_ratio == 1.0  # default


class TestBadActors:
    def test_ranking(self):
        data = [
            {"asset_id": 1, "asset_name": "A", "failure_count": 10, "total_downtime_hours": 50, "availability": 0.8},
            {"asset_id": 2, "asset_name": "B", "failure_count": 2, "total_downtime_hours": 5, "availability": 0.98},
            {"asset_id": 3, "asset_name": "C", "failure_count": 7, "total_downtime_hours": 30, "availability": 0.85},
        ]
        result = reliability_extended.rank_bad_actors(data, top_n=2)
        assert len(result.entries) == 2
        assert result.entries[0].asset_id == 1  # worst
        assert result.entries[0].composite_score >= result.entries[1].composite_score

    def test_empty(self):
        result = reliability_extended.rank_bad_actors([])
        assert len(result.entries) == 0


class TestRPN:
    def test_basic_rpn(self):
        fm_data = [
            {"name": "Bearing Wear", "count": 5, "avg_downtime_minutes": 120.0},
            {"name": "Seal Leak", "count": 2, "avg_downtime_minutes": 30.0},
        ]
        rpn = reliability_extended.compute_rpn(fm_data, total_events=10)
        assert len(rpn.entries) == 2
        assert rpn.entries[0].rpn >= rpn.entries[1].rpn  # sorted descending
        assert rpn.max_rpn == rpn.entries[0].rpn

    def test_empty_events(self):
        rpn = reliability_extended.compute_rpn([], total_events=0)
        assert len(rpn.entries) == 0


# =========================================================================
# manufacturing
# =========================================================================

class TestOEE:
    def test_perfect_oee(self):
        result = manufacturing.compute_oee(1.0, 1.0, 1.0)
        assert result.oee == 1.0

    def test_partial_oee(self):
        result = manufacturing.compute_oee(0.9, 0.8, 0.95)
        expected = 0.9 * 0.8 * 0.95
        assert abs(result.oee - round(expected, 4)) < 0.001


class TestPerformanceRate:
    def test_with_cycles(self):
        start = datetime(2024, 1, 1)
        exposures = [
            _make_exposure(start, 10.0, cycles=80.0),
            _make_exposure(start + timedelta(hours=10), 10.0, cycles=70.0),
        ]
        result = manufacturing.compute_performance_rate(exposures)
        assert result.total_cycles == 150.0
        assert result.total_operating_hours == 20.0
        assert result.actual_throughput == pytest.approx(7.5)

    def test_with_design_rate(self):
        start = datetime(2024, 1, 1)
        exposures = [_make_exposure(start, 10.0, cycles=80.0)]
        result = manufacturing.compute_performance_rate(exposures, design_cycles_per_hour=10.0)
        assert result.performance_rate == pytest.approx(0.8)


class TestDowntimeSplit:
    def test_split(self):
        events = [
            _make_event(datetime(2024, 1, 1), "failure", 120),
            _make_event(datetime(2024, 1, 2), "maintenance", 60),
            _make_event(datetime(2024, 1, 3), "failure", 60),
            _make_event(datetime(2024, 1, 4), "inspection", 30),
        ]
        result = manufacturing.compute_downtime_split(events)
        assert result.unplanned_count == 2
        assert result.planned_count == 2
        assert result.unplanned_downtime_hours == pytest.approx(3.0)
        assert result.planned_downtime_hours == pytest.approx(1.5)
        assert 0 < result.unplanned_ratio < 1


class TestMTBM:
    def test_mtbm(self):
        start = datetime(2024, 1, 1)
        exposures = [_make_exposure(start, 100.0)]
        events = [
            _make_event(start + timedelta(hours=30), "failure", 60),
            _make_event(start + timedelta(hours=60), "maintenance", 30),
        ]
        result = manufacturing.compute_mtbm(exposures, events)
        assert result.mtbm_hours == pytest.approx(50.0)
        assert result.maintenance_events == 2


class TestManufacturingAggregate:
    def test_aggregate(self):
        start = datetime(2024, 1, 1)
        exposures = [_make_exposure(start, 100.0, cycles=500.0)]
        events = [
            _make_event(start + timedelta(hours=50), "failure", 120),
        ]
        result = manufacturing.aggregate_manufacturing_kpis(exposures, events, availability=0.9)
        assert result.oee.oee > 0
        assert result.mtbm.mtbm_hours > 0
        assert result.downtime_split.unplanned_count == 1


# =========================================================================
# business
# =========================================================================

class TestCOUR:
    def test_basic_cour(self):
        result = business.compute_cour(10.0, 5, hourly_production_value=1000.0, avg_repair_cost=2000.0)
        assert result.lost_production_cost == 10_000.0
        assert result.repair_cost == 10_000.0
        assert result.total_cost == 20_000.0
        assert result.cost_per_failure == pytest.approx(4000.0)

    def test_zero_failures(self):
        result = business.compute_cour(0.0, 0)
        assert result.total_cost == 0.0


class TestPMOptimization:
    def test_wearout_pattern(self):
        result = business.compute_pm_optimization(shape=2.5, scale=1000.0)
        assert result.failure_pattern == "wearout"
        assert result.recommended_pm_hours > 0

    def test_random_pattern(self):
        result = business.compute_pm_optimization(shape=1.0, scale=1000.0)
        assert result.failure_pattern == "random"
        assert result.assessment == "pm_not_recommended"

    def test_infant_mortality(self):
        result = business.compute_pm_optimization(shape=0.5, scale=1000.0)
        assert result.failure_pattern == "infant_mortality"


class TestSpareDemand:
    def test_forecast(self):
        data = [
            {"part_name": "Bearing", "failure_rate_per_hour": 0.001},
            {"part_name": "Seal", "failure_rate_per_hour": 0.0005},
        ]
        result = business.forecast_spare_demand(data, horizon_hours=8760.0)
        assert len(result.forecasts) == 2
        assert result.total_expected_failures > 0
        # Bearing: 0.001 * 8760 ≈ 8.76 expected
        bearing = next(f for f in result.forecasts if f.part_name == "Bearing")
        assert abs(bearing.expected_failures - 8.76) < 0.01

    def test_empty(self):
        result = business.forecast_spare_demand([])
        assert result.total_expected_failures == 0.0


class TestHealthIndex:
    def test_healthy_asset(self):
        hi = business.compute_health_index(
            availability=0.97, mtbf_hours=500.0,
            unplanned_ratio=0.1, weibull_shape=1.3, oee=0.85,
        )
        assert hi.score >= 70
        assert hi.grade in ("A", "B")

    def test_unhealthy_asset(self):
        hi = business.compute_health_index(
            availability=0.5, mtbf_hours=50.0,
            unplanned_ratio=0.9, weibull_shape=3.5, oee=0.3,
            repair_trend_ratio=2.0,
        )
        assert hi.score < 55
        assert hi.grade in ("C", "D", "F")

    def test_grade_boundaries(self):
        assert business._grade(85) == "A"
        assert business._grade(70) == "B"
        assert business._grade(55) == "C"
        assert business._grade(40) == "D"
        assert business._grade(39) == "F"


# =========================================================================
# Integration: aggregate_kpis extended fields
# =========================================================================

class TestExtendedKPIs:
    def test_aggregate_includes_new_fields(self):
        start = datetime(2024, 1, 1)
        exposures = [
            ExposureLog(asset_id=1, start_time=start, end_time=start + timedelta(hours=50), hours=50),
            ExposureLog(asset_id=1, start_time=start + timedelta(hours=50), end_time=start + timedelta(hours=100), hours=50),
        ]
        events = [
            Event(asset_id=1, timestamp=exposures[0].end_time, event_type="failure", downtime_minutes=120),
        ]
        kpis = metrics.aggregate_kpis(exposures, events)
        assert "failure_rate" in kpis
        assert "total_exposure_hours" in kpis
        assert "failure_count" in kpis
        assert "total_events" in kpis
        assert kpis["failure_rate"] == pytest.approx(1 / 100)
        assert kpis["total_exposure_hours"] == pytest.approx(100.0)
