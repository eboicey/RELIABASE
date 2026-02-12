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

from reliabase import models, schemas
from reliabase.analytics import metrics, reporting, weibull, manufacturing, business, reliability_extended
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


# =========================================================================
# Extended Analytics Endpoints
# =========================================================================

def _build_failure_mode_details(session, details, events) -> list[dict]:
    """Build failure-mode dicts with avg downtime for RPN computation."""
    mode_data: dict[str, dict] = {}  # name -> {count, total_dt, category}
    event_map = {e.id: e for e in events}
    for d in details:
        mode = session.get(models.FailureMode, d.failure_mode_id)
        if not mode:
            continue
        if mode.name not in mode_data:
            mode_data[mode.name] = {"name": mode.name, "count": 0, "total_dt": 0.0, "category": mode.category}
        mode_data[mode.name]["count"] += 1
        evt = event_map.get(d.event_id)
        mode_data[mode.name]["total_dt"] += (evt.downtime_minutes or 0.0) if evt else 0.0
    result = []
    for md in mode_data.values():
        md["avg_downtime_minutes"] = md["total_dt"] / md["count"] if md["count"] > 0 else 0.0
        result.append(md)
    return result


@router.get("/asset/{asset_id}/extended", response_model=schemas.ExtendedAssetAnalytics)
def get_extended_asset_analytics(
    asset_id: int,
    session: SessionDep,
    n_bootstrap: int = 200,
    hourly_production_value: float = 500.0,
    avg_repair_cost: float = 1500.0,
    design_cycles_per_hour: Optional[float] = None,
    quality_rate: float = 1.0,
):
    """Unified analytics: reliability + manufacturing + business for one asset.

    Returns everything needed to evaluate an asset's reliability posture,
    manufacturing effectiveness, and financial impact in a single call.
    """
    asset, exposures, events, details = _load_asset_data(session, asset_id)

    # --- Core reliability KPIs ---
    kpi_data = metrics.aggregate_kpis(exposures, events)
    intervals = kpi_data.get("intervals_hours", [])
    censored = kpi_data.get("censored_flags", [])
    avail = kpi_data["availability"]
    mtbf = kpi_data["mtbf_hours"]
    mttr = kpi_data["mttr_hours"]
    failure_count = kpi_data["failure_count"]
    total_hours = kpi_data["total_exposure_hours"]

    # --- Weibull fit (needed by several downstream metrics) ---
    weibull_fit = None
    if intervals and any(not c for c in censored):
        try:
            weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)
        except Exception:
            pass

    # --- Extended reliability ---
    fr_out = None
    b10_out = None
    mttf_val = None
    repair_eff_out = None
    rpn_out = None

    fr = reliability_extended.compute_failure_rate(
        failure_count, total_hours,
        shape=weibull_fit.shape if weibull_fit else None,
        scale=weibull_fit.scale if weibull_fit else None,
        current_age_hours=total_hours,
    )
    fr_out = schemas.FailureRateOut(
        average_rate=fr.average_rate,
        instantaneous_rate=fr.instantaneous_rate,
        total_failures=fr.total_failures,
        total_hours=fr.total_hours,
    )

    if weibull_fit:
        b10 = reliability_extended.compute_b_life(weibull_fit.shape, weibull_fit.scale, 10.0)
        b10_out = schemas.BLifeOut(percentile=b10.percentile, life_hours=b10.life_hours)
        mttf_val = reliability_extended.compute_mttf(weibull_fit.shape, weibull_fit.scale)

    if intervals:
        re = reliability_extended.compute_repair_effectiveness(intervals)
        repair_eff_out = schemas.RepairEffectivenessOut(
            trend_ratio=re.trend_ratio, intervals_count=re.intervals_count, improving=re.improving,
        )

    # RPN
    fm_details = _build_failure_mode_details(session, details, events)
    total_events = len(events)
    if fm_details and total_events > 0:
        rpn = reliability_extended.compute_rpn(fm_details, total_events)
        rpn_out = schemas.RPNAnalysisOut(
            entries=[
                schemas.RPNEntryOut(
                    failure_mode=e.failure_mode, severity=e.severity,
                    occurrence=e.occurrence, detection=e.detection, rpn=e.rpn,
                )
                for e in rpn.entries
            ],
            max_rpn=rpn.max_rpn,
        )

    # --- Manufacturing ---
    mfg = manufacturing.aggregate_manufacturing_kpis(
        exposures, events, avail,
        design_cycles_per_hour=design_cycles_per_hour,
        quality_rate=quality_rate,
    )
    mfg_out = schemas.ManufacturingKPIsOut(
        oee=schemas.OEEOut(
            availability=mfg.oee.availability, performance=mfg.oee.performance,
            quality=mfg.oee.quality, oee=mfg.oee.oee,
        ),
        performance=schemas.PerformanceRateOut(
            actual_throughput=mfg.performance.actual_throughput,
            design_throughput=mfg.performance.design_throughput,
            performance_rate=mfg.performance.performance_rate,
            total_cycles=mfg.performance.total_cycles,
            total_operating_hours=mfg.performance.total_operating_hours,
        ),
        downtime_split=schemas.DowntimeSplitOut(
            planned_downtime_hours=mfg.downtime_split.planned_downtime_hours,
            unplanned_downtime_hours=mfg.downtime_split.unplanned_downtime_hours,
            total_downtime_hours=mfg.downtime_split.total_downtime_hours,
            unplanned_ratio=mfg.downtime_split.unplanned_ratio,
            planned_count=mfg.downtime_split.planned_count,
            unplanned_count=mfg.downtime_split.unplanned_count,
        ),
        mtbm=schemas.MTBMOut(
            mtbm_hours=mfg.mtbm.mtbm_hours,
            maintenance_events=mfg.mtbm.maintenance_events,
            total_operating_hours=mfg.mtbm.total_operating_hours,
        ),
    )

    # --- Business impact ---
    cour = business.compute_cour(
        mfg.downtime_split.unplanned_downtime_hours, failure_count,
        hourly_production_value=hourly_production_value,
        avg_repair_cost=avg_repair_cost,
    )
    cour_out = schemas.COUROut(
        total_cost=cour.total_cost, lost_production_cost=cour.lost_production_cost,
        repair_cost=cour.repair_cost, unplanned_downtime_hours=cour.unplanned_downtime_hours,
        failure_count=cour.failure_count, cost_per_failure=cour.cost_per_failure,
    )

    pm_out = None
    if weibull_fit:
        pm = business.compute_pm_optimization(weibull_fit.shape, weibull_fit.scale)
        pm_out = schemas.PMOptimizationOut(
            weibull_shape=pm.weibull_shape, failure_pattern=pm.failure_pattern,
            recommended_pm_hours=pm.recommended_pm_hours,
            current_pm_hours=pm.current_pm_hours,
            pm_ratio=pm.pm_ratio, assessment=pm.assessment,
        )

    # Health index
    hi = business.compute_health_index(
        availability=avail, mtbf_hours=mtbf,
        unplanned_ratio=mfg.downtime_split.unplanned_ratio,
        weibull_shape=weibull_fit.shape if weibull_fit else None,
        oee=mfg.oee.oee,
        repair_trend_ratio=repair_eff_out.trend_ratio if repair_eff_out else 1.0,
    )
    hi_out = schemas.AssetHealthIndexOut(score=hi.score, grade=hi.grade, components=hi.components)

    return schemas.ExtendedAssetAnalytics(
        asset_id=asset.id,
        asset_name=asset.name,
        mtbf_hours=mtbf,
        mttr_hours=mttr,
        availability=avail,
        failure_count=failure_count,
        total_exposure_hours=total_hours,
        failure_rate=fr_out,
        b10_life=b10_out,
        mttf_hours=mttf_val,
        repair_effectiveness=repair_eff_out,
        rpn=rpn_out,
        manufacturing=mfg_out,
        cour=cour_out,
        pm_optimization=pm_out,
        health_index=hi_out,
    )


@router.get("/fleet/bad-actors", response_model=list[schemas.BadActorEntryOut])
def get_bad_actors(
    session: SessionDep,
    top_n: int = 10,
):
    """Rank worst-performing assets across the fleet by composite bad-actor score."""
    assets = session.exec(select(models.Asset)).all()
    asset_data = []
    for asset in assets:
        exposures = session.exec(
            select(models.ExposureLog).where(models.ExposureLog.asset_id == asset.id)
        ).all()
        events = session.exec(
            select(models.Event).where(models.Event.asset_id == asset.id)
        ).all()
        kpi = metrics.aggregate_kpis(exposures, events)
        failure_events = [e for e in events if e.event_type.lower() == "failure"]
        total_dt_hrs = sum((e.downtime_minutes or 0) for e in failure_events) / 60.0
        asset_data.append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "failure_count": len(failure_events),
            "total_downtime_hours": total_dt_hrs,
            "availability": kpi["availability"],
        })

    ranked = reliability_extended.rank_bad_actors(asset_data, top_n=top_n)
    return [
        schemas.BadActorEntryOut(
            asset_id=e.asset_id, asset_name=e.asset_name,
            failure_count=e.failure_count, total_downtime_hours=e.total_downtime_hours,
            availability=e.availability, composite_score=e.composite_score,
        )
        for e in ranked.entries
    ]


@router.get("/asset/{asset_id}/conditional-reliability", response_model=schemas.ConditionalReliabilityOut)
def get_conditional_reliability(
    asset_id: int,
    session: SessionDep,
    current_age_hours: float = 0.0,
    mission_time_hours: float = 100.0,
):
    """Compute conditional reliability: P(survive additional mission_time | already survived current_age).

    Requires Weibull parameters from sufficient failure data.
    """
    asset, exposures, events, _ = _load_asset_data(session, asset_id)
    kpi_data = metrics.aggregate_kpis(exposures, events)
    intervals = kpi_data.get("intervals_hours", [])
    censored = kpi_data.get("censored_flags", [])

    if not intervals or not any(not c for c in censored):
        raise HTTPException(status_code=422, detail="Insufficient failure data for Weibull fit")

    weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored)

    # Default current_age to total operating hours if not specified
    if current_age_hours <= 0:
        current_age_hours = sum(e.hours for e in exposures if e.hours and e.hours > 0)

    cr = reliability_extended.compute_conditional_reliability(
        weibull_fit.shape, weibull_fit.scale, current_age_hours, mission_time_hours,
    )
    return schemas.ConditionalReliabilityOut(
        current_age=cr.current_age,
        mission_time=cr.mission_time,
        conditional_reliability=cr.conditional_reliability,
    )


@router.get("/fleet/spare-demand", response_model=schemas.SpareDemandOut)
def get_spare_demand_forecast(
    session: SessionDep,
    horizon_hours: float = 8760.0,
):
    """Forecast spare-part demand across the fleet for a planning horizon.

    Uses historical failure rates per part to project Poisson-based demand.
    """
    # Aggregate part-level failure rates from EventFailureDetail.part_replaced
    details = session.exec(select(models.EventFailureDetail)).all()
    events = session.exec(select(models.Event)).all()
    exposures = session.exec(select(models.ExposureLog)).all()

    total_hours = sum(e.hours for e in exposures if e.hours and e.hours > 0)
    if total_hours <= 0:
        return schemas.SpareDemandOut(horizon_hours=horizon_hours)

    # Count replacements per part name
    part_counts: dict[str, int] = {}
    for d in details:
        part_name = d.part_replaced or "Unknown"
        part_counts[part_name] = part_counts.get(part_name, 0) + 1

    part_data = [
        {"part_name": name, "failure_rate_per_hour": count / total_hours}
        for name, count in part_counts.items()
        if name != "Unknown"
    ]

    if not part_data:
        return schemas.SpareDemandOut(horizon_hours=horizon_hours)

    result = business.forecast_spare_demand(part_data, horizon_hours)
    return schemas.SpareDemandOut(
        horizon_hours=result.horizon_hours,
        forecasts=[
            schemas.SparePartForecastOut(
                part_name=f.part_name, expected_failures=f.expected_failures,
                lower_bound=f.lower_bound, upper_bound=f.upper_bound,
            )
            for f in result.forecasts
        ],
        total_expected_failures=result.total_expected_failures,
    )


@router.get("/fleet/health-summary", response_model=list[schemas.AssetHealthIndexOut])
def get_fleet_health_summary(
    session: SessionDep,
    limit: int = 50,
):
    """Quick health score for every asset — suitable for dashboard heatmaps."""
    assets = session.exec(select(models.Asset).limit(limit)).all()
    results = []
    for asset in assets:
        exposures = session.exec(
            select(models.ExposureLog).where(models.ExposureLog.asset_id == asset.id)
        ).all()
        events = session.exec(
            select(models.Event).where(models.Event.asset_id == asset.id)
        ).all()
        kpi = metrics.aggregate_kpis(exposures, events)
        dt_split = manufacturing.compute_downtime_split(events)
        perf = manufacturing.compute_performance_rate(exposures)
        oee = manufacturing.compute_oee(kpi["availability"], perf.performance_rate)

        hi = business.compute_health_index(
            availability=kpi["availability"],
            mtbf_hours=kpi["mtbf_hours"],
            unplanned_ratio=dt_split.unplanned_ratio,
            oee=oee.oee,
        )
        results.append(schemas.AssetHealthIndexOut(
            score=hi.score, grade=hi.grade, components=hi.components,
        ))
    return results