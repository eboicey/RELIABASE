"""Weibull fitting utilities (2-parameter, bootstrap CI)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Tuple

import numpy as np
from scipy import optimize, stats


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


def _neg_log_likelihood(log_params: np.ndarray, durations: np.ndarray, censored: np.ndarray) -> float:
    """Stable negative log-likelihood for Weibull with censoring.

    Computation is performed in log-space with clipping to avoid overflow when
    durations are large or very small.
    """
    log_shape, log_scale = log_params
    log_shape = float(np.clip(log_shape, np.log(1e-6), np.log(1e6)))
    log_scale = float(np.clip(log_scale, np.log(1e-6), np.log(1e9)))
    shape = np.exp(log_shape)
    scale = np.exp(log_scale)

    eps = 1e-12
    t = np.maximum(durations, eps)
    log_t = np.log(t)
    observed = ~censored

    exp_arg = shape * (log_t - log_scale)
    exp_arg_clipped = np.clip(exp_arg, -700, 700)  # prevents overflow in exp

    log_pdf = np.log(shape) + (shape - 1) * (log_t - log_scale) - np.exp(exp_arg_clipped)
    log_sf = -np.exp(exp_arg_clipped)

    ll = np.sum(log_pdf[observed]) + np.sum(log_sf[censored])
    return -float(ll)


def fit_weibull_mle_censored(durations: Sequence[float], censored_flags: Sequence[bool] | None = None) -> WeibullFit:
    """Fit Weibull with optional right-censoring using MLE."""
    durations_arr = np.array(list(durations), dtype=float)
    if durations_arr.size == 0:
        raise ValueError("Cannot fit Weibull to empty data")
    if censored_flags is None:
        censored_arr = np.zeros_like(durations_arr, dtype=bool)
    else:
        censored_arr = np.array(list(censored_flags), dtype=bool)
        if censored_arr.size != durations_arr.size:
            raise ValueError("durations and censored_flags must be same length")

    uncensored_guess = fit_weibull_mle(durations_arr[~censored_arr]) if np.any(~censored_arr) else None
    init_shape = uncensored_guess.shape if uncensored_guess else 1.5
    init_scale = uncensored_guess.scale if uncensored_guess else max(float(np.median(durations_arr)), 1e-6)
    result = optimize.minimize(
        _neg_log_likelihood,
        x0=np.array([np.log(init_shape), np.log(init_scale)]),
        args=(durations_arr, censored_arr),
        method="L-BFGS-B",
        bounds=((np.log(1e-6), np.log(1e6)), (np.log(1e-6), np.log(1e9))),
    )
    if not result.success:
        raise RuntimeError(f"Weibull MLE failed: {result.message}")
    shape = float(np.exp(np.clip(result.x[0], np.log(1e-6), np.log(1e6))))
    scale = float(np.exp(np.clip(result.x[1], np.log(1e-6), np.log(1e9))))
    loglike = -_neg_log_likelihood(result.x, durations_arr, censored_arr)
    return WeibullFit(shape=shape, scale=scale, log_likelihood=loglike)


def bootstrap_weibull_ci(
    data: Sequence[float],
    censored_flags: Sequence[bool] | None = None,
    n_bootstrap: int = 1000,
    alpha: float = 0.05,
    allow_uncensored_fallback: bool = True,
) -> WeibullCI:
    """Bootstrap confidence intervals for shape/scale parameters with optional censoring."""
    arr = np.array(list(data), dtype=float)
    if arr.size == 0:
        raise ValueError("Cannot bootstrap Weibull on empty data")
    if censored_flags is None:
        censored_arr = np.zeros_like(arr, dtype=bool)
    else:
        censored_arr = np.array(list(censored_flags), dtype=bool)
        if censored_arr.size != arr.size:
            raise ValueError("data and censored_flags must be same length")

    boot_shapes = []
    boot_scales = []
    rng = np.random.default_rng()
    for _ in range(n_bootstrap):
        idx = rng.integers(0, arr.size, size=arr.size)
        sample = arr[idx]
        sample_cens = censored_arr[idx]
        try:
            fit = fit_weibull_mle_censored(sample, sample_cens)
        except Exception:
            if allow_uncensored_fallback:
                fit = fit_weibull_mle(sample)
            else:
                raise
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
