from datetime import datetime, timedelta

import numpy as np

from reliabase.analytics import metrics, weibull
from reliabase.models import Event, ExposureLog


def _make_exposure(start: datetime, hours: float) -> ExposureLog:
    return ExposureLog(asset_id=1, start_time=start, end_time=start + timedelta(hours=hours), hours=hours, cycles=0)


def test_time_between_failures_with_censoring():
    start = datetime(2023, 1, 1)
    exposures = [
        _make_exposure(start, 50),
        _make_exposure(start + timedelta(hours=50), 60),
        _make_exposure(start + timedelta(hours=110), 40),
    ]
    failures = [
        Event(asset_id=1, timestamp=exposures[1].end_time, event_type="failure"),
    ]
    result = metrics.derive_time_between_failures(exposures, failures)
    assert len(result.intervals_hours) == 2  # one failure interval + censored tail
    assert result.censored_flags[-1] is True
    assert result.intervals_hours[0] > 0


def test_weibull_censored_fit_and_ci():
    durations = [100.0, 120.0, 80.0, 150.0]
    censored = [False, False, True, False]
    fit = weibull.fit_weibull_mle_censored(durations, censored)
    assert fit.shape > 0 and fit.scale > 0
    ci = weibull.bootstrap_weibull_ci(durations, censored, n_bootstrap=50)
    assert ci.shape_ci[0] < ci.shape_ci[1]


def test_reliability_curves_monotonic():
    fit = weibull.WeibullFit(shape=2.0, scale=100.0, log_likelihood=0)
    times = np.linspace(0, 200, 20)
    curves = weibull.reliability_curves(fit.shape, fit.scale, times)
    assert np.all(np.diff(curves.reliability) <= 1e-6)
    assert len(curves.hazard) == len(times)
