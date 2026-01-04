"""Weibull fitting utilities (2-parameter, bootstrap CI)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

import numpy as np
from scipy import stats


@dataclass
class WeibullFit:
    shape: float
    scale: float
    log_likelihood: float


@dataclass
class WeibullCI:
    shape_ci: Tuple[float, float]
    scale_ci: Tuple[float, float]


@dataclass
class ReliabilityCurves:
    times: np.ndarray
    reliability: np.ndarray
    hazard: np.ndarray


def fit_weibull_mle(data: Iterable[float]) -> WeibullFit:
    """Fit a 2-parameter Weibull distribution via SciPy MLE."""
    arr = np.array(list(data), dtype=float)
    if arr.size == 0:
        raise ValueError("Cannot fit Weibull to empty data")
    c, loc, scale = stats.weibull_min.fit(arr, floc=0)  # enforce 2-parameter
    loglike = np.sum(stats.weibull_min.logpdf(arr, c, scale=scale))
    return WeibullFit(shape=c, scale=scale, log_likelihood=loglike)


def bootstrap_weibull_ci(data: Sequence[float], n_bootstrap: int = 1000, alpha: float = 0.05) -> WeibullCI:
    """Bootstrap confidence intervals for shape/scale parameters."""
    arr = np.array(list(data), dtype=float)
    if arr.size == 0:
        raise ValueError("Cannot bootstrap Weibull on empty data")
    boot_shapes = []
    boot_scales = []
    rng = np.random.default_rng()
    for _ in range(n_bootstrap):
        sample = rng.choice(arr, size=arr.size, replace=True)
        fit = fit_weibull_mle(sample)
        boot_shapes.append(fit.shape)
        boot_scales.append(fit.scale)
    lower = alpha / 2
    upper = 1 - alpha / 2
    return WeibullCI(
        shape_ci=(float(np.quantile(boot_shapes, lower)), float(np.quantile(boot_shapes, upper))),
        scale_ci=(float(np.quantile(boot_scales, lower)), float(np.quantile(boot_scales, upper))),
    )


def reliability_curves(shape: float, scale: float, times: Sequence[float]) -> ReliabilityCurves:
    """Compute reliability R(t) and hazard h(t) for given times."""
    t = np.array(times, dtype=float)
    dist = stats.weibull_min(c=shape, scale=scale)
    reliability = 1 - dist.cdf(t)
    hazard = dist.pdf(t) / np.maximum(reliability, 1e-12)
    return ReliabilityCurves(times=t, reliability=reliability, hazard=hazard)
