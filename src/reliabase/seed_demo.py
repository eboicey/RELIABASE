"""Demo dataset generator CLI."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

import typer
from sqlmodel import Session

from reliabase.config import init_db, get_engine
from reliabase.models import Asset, Event, ExposureLog, FailureMode, EventFailureDetail, Part, PartInstall

app = typer.Typer(help="RELIABASE demo data seeding")


def _hours(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


def seed_demo_dataset(session: Session) -> None:
    random.seed(42)
    assets = [
        Asset(name="Compressor A", type="compressor", serial="COMP-A-01"),
        Asset(name="Pump B", type="pump", serial="PUMP-B-02"),
    ]
    for asset in assets:
        session.add(asset)
    session.commit()

    failure_modes = [
        FailureMode(name="Seal leak", category="mechanical"),
        FailureMode(name="Bearing wear", category="mechanical"),
        FailureMode(name="Overheat", category="thermal"),
    ]
    session.add_all(failure_modes)
    session.commit()

    parts = [
        Part(name="Bearing", part_number="BRG-100"),
        Part(name="Seal", part_number="SEAL-200"),
    ]
    session.add_all(parts)
    session.commit()

    now = datetime.utcnow()
    exposures: list[ExposureLog] = []
    events: list[Event] = []
    details: list[EventFailureDetail] = []
    installs: list[PartInstall] = []

    for asset in assets:
        start = now - timedelta(days=120)
        for i in range(24):
            period_hours = random.uniform(80, 140)
            end = start + timedelta(hours=period_hours)
            exposures.append(
                ExposureLog(
                    asset_id=asset.id,
                    start_time=start,
                    end_time=end,
                    hours=period_hours,
                    cycles=random.uniform(10, 40),
                )
            )
            start = end

        failure_indices = [6, 13, 20]
        for idx in failure_indices:
            failure_ts = exposures[idx].end_time
            downtime = random.uniform(30, 180)
            events.append(
                Event(
                    asset_id=asset.id,
                    timestamp=failure_ts,
                    event_type="failure",
                    downtime_minutes=downtime,
                    description=f"Failure at segment {idx}",
                )
            )

        maint_indices = [9, 18]
        for idx in maint_indices:
            ts = exposures[idx].end_time
            events.append(
                Event(
                    asset_id=asset.id,
                    timestamp=ts,
                    event_type="maintenance",
                    downtime_minutes=random.uniform(10, 60),
                    description=f"PM at segment {idx}",
                )
            )

    session.add_all(exposures + events)
    session.commit()

    for event in events:
        if event.event_type == "failure":
            fm = random.choice(failure_modes)
            details.append(
                EventFailureDetail(
                    event_id=event.id,
                    failure_mode_id=fm.id,
                    root_cause=random.choice(["wear", "contamination", "overload"]),
                    corrective_action=random.choice(["replace seal", "replace bearing", "clean"]),
                    part_replaced=random.choice(["Seal", "Bearing", None]),
                )
            )
    session.add_all(details)
    session.commit()

    for part in parts:
        for asset in assets:
            install_time = now - timedelta(days=random.randint(30, 90))
            installs.append(
                PartInstall(
                    asset_id=asset.id,
                    part_id=part.id,
                    install_time=install_time,
                    remove_time=None,
                )
            )
    session.add_all(installs)
    session.commit()


@app.command()
def main():
    """Generate a coherent demo dataset in the configured database."""
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        seed_demo_dataset(session)
    typer.echo("Demo dataset generated.")


if __name__ == "__main__":
    app()
