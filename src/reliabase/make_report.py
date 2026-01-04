"""Asset report generator CLI."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import typer
from sqlmodel import Session, select

from reliabase.analytics import metrics, reporting, weibull
from reliabase.config import get_engine, init_db
from reliabase.models import Asset, Event, ExposureLog, EventFailureDetail, FailureMode

app = typer.Typer(help="Generate reliability packet for an asset")


def _load_data(session: Session, asset_id: int):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise typer.BadParameter(f"Asset {asset_id} not found")
    exposures = session.exec(select(ExposureLog).where(ExposureLog.asset_id == asset_id)).all()
    events = session.exec(select(Event).where(Event.asset_id == asset_id)).all()
    details = session.exec(select(EventFailureDetail).join(FailureMode).where(EventFailureDetail.event_id.in_([e.id for e in events]))).all()
    return asset, exposures, events, details


def _failure_counts(details: list[EventFailureDetail]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in details:
        name = d.failure_mode.name if d.failure_mode else "unknown"
        counts[name] = counts.get(name, 0) + 1
    return counts


@app.command()
def main(asset_id: int, output_dir: Path = Path("./examples")):
    """Generate a PDF report for the given asset ID."""
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        asset, exposures, events, details = _load_data(session, asset_id)
        kpis = metrics.aggregate_kpis(exposures, events)
        intervals = kpis.get("intervals_hours", [])
        censored = kpis.get("censored_flags", [])
        weibull_fit = weibull.fit_weibull_mle_censored(intervals, censored) if intervals else None
        ci = weibull.bootstrap_weibull_ci(intervals, censored, n_bootstrap=200) if intervals else None
        times = np.linspace(0, max(intervals) * 1.2 if intervals else 1.0, 50)
        curves = (
            weibull.reliability_curves(weibull_fit.shape, weibull_fit.scale, times)
            if weibull_fit
            else weibull.ReliabilityCurves(times=np.array([]), reliability=np.array([]), hazard=np.array([]))
        )
        failure_counts = _failure_counts(details)

        context = {
            "asset": asset,
            "metrics": kpis,
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

        pdf_path = reporting.generate_asset_report(output_dir, context)
    typer.echo(f"Generated report at {pdf_path}")


if __name__ == "__main__":
    app()
