"""Demo dataset generator CLI."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Dict

import typer
from sqlmodel import Session, delete

from reliabase.config import init_db, get_engine
from reliabase.models import Asset, Event, ExposureLog, FailureMode, EventFailureDetail, Part, PartInstall

app = typer.Typer(help="RELIABASE demo data seeding")


def _clear_existing(session: Session) -> None:
    """Wipe existing rows so demo seeding is repeatable."""
    for model in (EventFailureDetail, Event, ExposureLog, PartInstall, Part, FailureMode, Asset):
        session.exec(delete(model))
    session.commit()


def seed_demo_dataset(session: Session, reset: bool = True) -> Dict[str, int]:
    """Create a richer, reproducible demo dataset.

    Parameters
    ----------
    session: SQLModel session bound to the active engine.
    reset: when True (default), existing rows are cleared before insertion.
    """
    if reset:
        _clear_existing(session)

    random.seed(42)
    now = datetime.now(timezone.utc)

    assets = [
        Asset(name="Compressor A", type="compressor", serial="COMP-A-01"),
        Asset(name="Pump B", type="pump", serial="PUMP-B-02"),
        Asset(name="Conveyor C", type="conveyor", serial="CONV-C-03"),
        Asset(name="Fan D", type="fan", serial="FAN-D-04"),
    ]
    session.add_all(assets)
    session.commit()

    failure_modes = [
        FailureMode(name="Seal leak", category="mechanical"),
        FailureMode(name="Bearing wear", category="mechanical"),
        FailureMode(name="Overheat", category="thermal"),
        FailureMode(name="Vibration", category="mechanical"),
        FailureMode(name="Electrical fault", category="electrical"),
    ]
    session.add_all(failure_modes)
    session.commit()

    parts = [
        Part(name="Bearing", part_number="BRG-100"),
        Part(name="Seal", part_number="SEAL-200"),
        Part(name="Motor", part_number="MTR-300"),
        Part(name="Coupling", part_number="COUP-400"),
    ]
    session.add_all(parts)
    session.commit()

    exposures: list[ExposureLog] = []
    events: list[Event] = []
    details: list[EventFailureDetail] = []
    installs: list[PartInstall] = []

    for asset in assets:
        start = now - timedelta(days=180)
        asset_exposures: list[ExposureLog] = []
        for _ in range(30):
            duration_hours = random.uniform(60, 140)
            end = start + timedelta(hours=duration_hours)
            asset_exposures.append(
                ExposureLog(
                    asset_id=asset.id,
                    start_time=start,
                    end_time=end,
                    hours=duration_hours,
                    cycles=random.uniform(8, 60),
                )
            )
            start = end + timedelta(hours=random.uniform(1, 8))

        exposures.extend(asset_exposures)

        failure_indices = random.sample(range(5, len(asset_exposures) - 2), 4)
        maintenance_indices = random.sample(range(4, len(asset_exposures) - 2), 3)
        inspection_indices = random.sample(range(6, len(asset_exposures) - 2), 2)

        for idx in failure_indices:
            failure_log = asset_exposures[idx]
            events.append(
                Event(
                    asset_id=asset.id,
                    timestamp=failure_log.end_time,
                    event_type="failure",
                    downtime_minutes=random.uniform(40, 240),
                    description=f"Failure after segment {idx} for {asset.name}",
                )
            )

        for idx in maintenance_indices:
            log = asset_exposures[idx]
            events.append(
                Event(
                    asset_id=asset.id,
                    timestamp=log.end_time,
                    event_type="maintenance",
                    downtime_minutes=random.uniform(15, 90),
                    description=f"Preventive maintenance at segment {idx}",
                )
            )

        for idx in inspection_indices:
            log = asset_exposures[idx]
            events.append(
                Event(
                    asset_id=asset.id,
                    timestamp=log.end_time,
                    event_type="inspection",
                    downtime_minutes=random.uniform(5, 30),
                    description=f"Inspection after segment {idx}",
                )
            )

        for part in parts:
            install_time = now - timedelta(days=random.randint(20, 120))
            remove_time = None if random.random() > 0.3 else install_time + timedelta(days=random.randint(10, 60))
            installs.append(
                PartInstall(
                    asset_id=asset.id,
                    part_id=part.id,
                    install_time=install_time,
                    remove_time=remove_time,
                )
            )

    session.add_all(exposures + events + installs)
    session.commit()

    failure_pool = ["wear", "contamination", "overload", "misalignment", "electrical noise"]
    actions_pool = ["replace seal", "replace bearing", "rebalance", "rewire", "clean and lube"]

    for event in events:
        if event.event_type == "failure":
            fm = random.choice(failure_modes)
            details.append(
                EventFailureDetail(
                    event_id=event.id,
                    failure_mode_id=fm.id,
                    root_cause=random.choice(failure_pool),
                    corrective_action=random.choice(actions_pool),
                    part_replaced=random.choice(["Seal", "Bearing", "Motor", None]),
                )
            )

    session.add_all(details)
    session.commit()

    return {
        "assets": len(assets),
        "exposures": len(exposures),
        "events": len(events),
        "failure_details": len(details),
        "parts": len(parts),
        "installs": len(installs),
    }


@app.command()
def main(
    reset: bool = typer.Option(True, "--reset/--no-reset", help="Clear existing tables before seeding"),
    database_url: str | None = typer.Option(None, "--database-url", help="Override database URL"),
):
    """Generate a coherent demo dataset in the configured database."""
    init_db(database_url=database_url)
    engine = get_engine(database_url)
    with Session(engine) as session:
        summary = seed_demo_dataset(session, reset=reset)
    typer.echo(
        "Demo dataset generated "
        f"({summary['assets']} assets, {summary['events']} events, {summary['exposures']} exposures, "
        f"{summary['failure_details']} failure details, {summary['parts']} parts)."
    )
    engine.dispose()


if __name__ == "__main__":
    app()
