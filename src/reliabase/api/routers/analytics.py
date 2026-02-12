"""Analytics API endpoints for Weibull analysis and report generation."""
from __future__ import annotations

import io
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import select

from reliabase import models
from reliabase.analytics import metrics, reporting, weibull
from reliabase.api.deps import SessionDep


router = APIRouter(prefix="/analytics", tags=["analytics"])


class WeibullParams(BaseModel):
    """Weibull distribution parameters with confidence intervals."""
    shape: float
    scale: float
    log_likelihood: float
    shape_ci: tuple[float, float]
    scale_ci: tuple[float, float]


class ReliabilityCurveData(BaseModel):
    """Time series for reliability and hazard curves."""
    times: list[float]
    reliability: list[float]
    hazard: list[float]


class KPIMetrics(BaseModel):
    """Key reliability performance indicators."""
    mtbf_hours: float
    mttr_hours: float
    availability: float
    failure_count: int
    total_exposure_hours: float


class FailureModeCount(BaseModel):
    """Failure mode with occurrence count."""
    name: str
    count: int
    category: Optional[str] = None


class EventSummary(BaseModel):
    """Summary of an event for timeline."""
    id: int
    timestamp: str
    event_type: str
    downtime_minutes: float
    description: Optional[str] = None


class AssetAnalytics(BaseModel):
    """Complete analytics data for an asset."""
    asset_id: int
    asset_name: str
    kpis: KPIMetrics
    weibull: Optional[WeibullParams] = None
    curves: Optional[ReliabilityCurveData] = None
    failure_modes: list[FailureModeCount]
    recent_events: list[EventSummary]
    intervals_hours: list[float]
    censored_flags: list[bool]


def _load_asset_data(session, asset_id: int):
    """Load all required data for asset analytics."""
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
    
    exposures = session.exec(
        select(models.ExposureLog).where(models.ExposureLog.asset_id == asset_id)
    ).all()
    events = session.exec(
        select(models.Event).where(models.Event.asset_id == asset_id)
    ).all()
    
    # Get failure details with modes
    event_ids = [e.id for e in events]
    details = []
    if event_ids:
        details = session.exec(
            select(models.EventFailureDetail)
            .where(models.EventFailureDetail.event_id.in_(event_ids))
        ).all()
    
    return asset, exposures, events, details


def _compute_failure_counts(session, details: list) -> dict[str, tuple[int, str | None]]:
    """Compute failure mode counts with category info."""
    counts: dict[str, tuple[int, str | None]] = {}
    for d in details:
        mode = session.get(models.FailureMode, d.failure_mode_id)
        if mode:
            name = mode.name
            category = mode.category
            current_count, _ = counts.get(name, (0, category))
            counts[name] = (current_count + 1, category)
    return counts


@router.get("/asset/{asset_id}", response_model=AssetAnalytics)
def get_asset_analytics(
    asset_id: int,
    session: SessionDep,
    n_bootstrap: int = 200,
):
    """Get comprehensive reliability analytics for a specific asset.
    
    Returns Weibull analysis, KPIs, reliability curves, and failure mode breakdown.
    """
    asset, exposures, events, details = _load_asset_data(session, asset_id)
    
    # Compute KPIs
    kpi_data = metrics.aggregate_kpis(exposures, events)
    intervals = kpi_data.get("intervals_hours", [])
    censored = kpi_data.get("censored_flags", [])
    
    failure_events = [e for e in events if e.event_type.lower() == "failure"]
    total_exposure = sum(log.hours or 0 for log in exposures)
    
    kpis = KPIMetrics(
        mtbf_hours=kpi_data.get("mtbf_hours", 0),
        mttr_hours=kpi_data.get("mttr_hours", 0),
        availability=kpi_data.get("availability", 0),
        failure_count=len(failure_events),
        total_exposure_hours=total_exposure,
    )
    
    # Weibull analysis
    weibull_params = None
    curves_data = None
    
    if intervals and any(not c for c in censored):  # Need at least one uncensored interval
        try:
            weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
            ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=n_bootstrap)
            
            weibull_params = WeibullParams(
                shape=weibull_fit.shape,
                scale=weibull_fit.scale,
                log_likelihood=weibull_fit.log_likelihood,
                shape_ci=ci.shape_ci,
                scale_ci=ci.scale_ci,
            )
            
            # Generate curves
            max_time = max(intervals) * 1.5 if intervals else 1000.0
            times = np.linspace(0, max_time, 100).tolist()
            curves = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)
            
            curves_data = ReliabilityCurveData(
                times=times,
                reliability=[float(r) for r in curves.reliability],
                hazard=[float(h) for h in curves.hazard],
            )
        except Exception:
            # Weibull fitting failed - return None for these fields
            pass
    
    # Failure mode counts
    failure_counts = _compute_failure_counts(session, details)
    failure_modes = [
        FailureModeCount(name=name, count=count, category=category)
        for name, (count, category) in sorted(
            failure_counts.items(), key=lambda x: x[1][0], reverse=True
        )
    ]
    
    # Recent events
    recent_events = [
        EventSummary(
            id=e.id,
            timestamp=e.timestamp.isoformat(),
            event_type=e.event_type,
            downtime_minutes=e.downtime_minutes or 0.0,
            description=e.description,
        )
        for e in sorted(events, key=lambda x: x.timestamp, reverse=True)[:20]
    ]
    
    return AssetAnalytics(
        asset_id=asset.id,
        asset_name=asset.name,
        kpis=kpis,
        weibull=weibull_params,
        curves=curves_data,
        failure_modes=failure_modes,
        recent_events=recent_events,
        intervals_hours=intervals,
        censored_flags=censored,
    )


@router.get("/asset/{asset_id}/report", response_class=Response)
def download_asset_report(
    asset_id: int,
    session: SessionDep,
    n_bootstrap: int = 200,
):
    """Download a PDF reliability report for the specified asset.
    
    Generates Weibull analysis, reliability curves, Pareto charts, and event timeline.
    """
    asset, exposures, events, details = _load_asset_data(session, asset_id)
    
    # Compute everything needed for the report
    kpi_data = metrics.aggregate_kpis(exposures, events)
    intervals = kpi_data.get("intervals_hours", [])
    censored = kpi_data.get("censored_flags", [])
    
    # Weibull fitting
    weibull_fit = None
    ci = None
    curves = None
    
    if intervals and any(not c for c in censored):
        try:
            weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
            ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=n_bootstrap)
            times = np.linspace(0, max(intervals) * 1.2 if intervals else 1.0, 50)
            curves = weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)
        except Exception:
            pass
    
    if curves is None:
        curves = weibull.ReliabilityCurves(
            times=np.array([]),
            reliability=np.array([]),
            hazard=np.array([]),
        )
    
    # Failure counts
    failure_counts: dict[str, int] = {}
    for d in details:
        mode = session.get(models.FailureMode, d.failure_mode_id)
        name = mode.name if mode else "Unknown"
        failure_counts[name] = failure_counts.get(name, 0) + 1
    
    # Build report context
    context = {
        "asset": asset,
        "metrics": kpi_data,
        "weibull": {
            "shape": weibull_fit.shape if weibull_fit else 0,
            "scale": weibull_fit.scale if weibull_fit else 0,
            "shape_ci": ci.shape_ci if ci else (0, 0),
            "scale_ci": ci.scale_ci if ci else (0, 0),
        },
        "curves": {
            "times": list(curves.times),
            "reliability": list(curves.reliability),
            "hazard": list(curves.hazard),
        },
        "events": [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "downtime_minutes": e.downtime_minutes or 0.0,
                "description": e.description,
            }
            for e in events
        ],
        "failure_counts": failure_counts,
    }
    
    # Generate PDF to temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        pdf_path = reporting.generate_asset_report(output_dir, context)
        
        # Read PDF content
        pdf_content = pdf_path.read_bytes()
    
    filename = f"asset_{asset_id}_reliability_report.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/fleet", response_model=list[AssetAnalytics])
def get_fleet_analytics(
    session: SessionDep,
    limit: int = 50,
):
    """Get analytics summary for all assets (fleet view).
    
    Returns basic analytics for each asset without full Weibull bootstrap.
    """
    assets = session.exec(select(models.Asset).limit(limit)).all()
    
    results = []
    for asset in assets:
        try:
            analytics = get_asset_analytics(
                asset_id=asset.id,
                session=session,
                n_bootstrap=50,  # Reduced for fleet view
            )
            results.append(analytics)
        except HTTPException:
            # Skip assets with errors
            continue
    
    return results
