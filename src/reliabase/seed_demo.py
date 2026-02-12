"""Demo dataset generator CLI.

Produces a rich, realistic demo dataset that fully exercises every feature
and metric in RELIABASE:

* 10 assets across 4 equipment types with differentiated behaviours
* Wear-out, random, and infant-mortality Weibull failure patterns
* Asset-specific dominant failure modes (correlated, not random)
* Enough failure intervals per asset (8-15) for stable Weibull fits and CIs
* Clear "bad actor" differentiation for fleet ranking
* Varying downtime severity for meaningful RPN/FMEA
* Correlated root causes, corrective actions, and part replacements
* Realistic exposure durations and cycle rates per equipment type
* Maintenance events scheduled relative to failure patterns
* Part installs with install/remove lifecycle
* 365-day observation window with in_service_dates set
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone, date
from typing import Dict, List, Tuple

import typer
from sqlmodel import Session, delete

from reliabase.config import init_db, get_engine
from reliabase.models import (
    Asset,
    Event,
    EventFailureDetail,
    ExposureLog,
    FailureMode,
    Part,
    PartInstall,
)

app = typer.Typer(help="RELIABASE demo data seeding")


# ---------------------------------------------------------------------------
# Asset profile definitions
# ---------------------------------------------------------------------------

# Each profile controls exposure generation + failure placement to produce
# the desired Weibull shape (β) so every analytics metric works well.
#
#   β > 1.5  → wear-out   (failures cluster later in life)
#   β ≈ 1.0  → random     (failures uniformly spread)
#   β < 0.9  → infant mortality (failures cluster early)

ASSET_PROFILES: list[dict] = [
    # ---------- Compressors ----------
    {
        "name": "Compressor A",
        "type": "compressor",
        "serial": "COMP-A-001",
        "in_service_date": date(2024, 1, 15),
        "notes": "Primary air compressor, Line 1. 150 HP screw type.",
        "failure_pattern": "wearout",         # β ≈ 2.2
        "n_exposures": 55,
        "hours_range": (70, 130),             # 7-day shifts
        "cycles_per_hour": (1.5, 3.0),        # moderate cycling
        "n_failures": 10,
        "n_maintenance": 6,
        "n_inspections": 4,
        "dominant_modes": ["Bearing wear", "Vibration"],
        "secondary_modes": ["Overheat"],
        "failure_downtime_range": (90, 360),  # high severity
    },
    {
        "name": "Compressor B",
        "type": "compressor",
        "serial": "COMP-B-002",
        "in_service_date": date(2024, 6, 1),
        "notes": "Backup compressor, Line 1. 100 HP reciprocating.",
        "failure_pattern": "random",          # β ≈ 1.0
        "n_exposures": 40,
        "hours_range": (50, 100),
        "cycles_per_hour": (1.0, 2.5),
        "n_failures": 5,
        "n_maintenance": 4,
        "n_inspections": 3,
        "dominant_modes": ["Overheat", "Electrical fault"],
        "secondary_modes": ["Vibration"],
        "failure_downtime_range": (30, 150),
    },
    {
        "name": "Compressor C",
        "type": "compressor",
        "serial": "COMP-C-003",
        "in_service_date": date(2025, 9, 10),
        "notes": "New install, showing early issues. 200 HP centrifugal.",
        "failure_pattern": "infant",          # β ≈ 0.7
        "n_exposures": 25,
        "hours_range": (60, 110),
        "cycles_per_hour": (2.0, 4.0),
        "n_failures": 8,
        "n_maintenance": 2,
        "n_inspections": 2,
        "dominant_modes": ["Electrical fault", "Seal leak"],
        "secondary_modes": ["Vibration"],
        "failure_downtime_range": (20, 180),
    },
    # ---------- Pumps ----------
    {
        "name": "Pump A",
        "type": "pump",
        "serial": "PUMP-A-004",
        "in_service_date": date(2023, 11, 20),
        "notes": "Chemical transfer pump. Chronic seal problems — bad actor.",
        "failure_pattern": "wearout",         # β ≈ 1.8
        "n_exposures": 55,
        "hours_range": (60, 120),
        "cycles_per_hour": (5.0, 12.0),       # high cycling
        "n_failures": 15,                     # BAD ACTOR — most failures
        "n_maintenance": 5,
        "n_inspections": 3,
        "dominant_modes": ["Seal leak", "Seal leak", "Bearing wear"],
        "secondary_modes": ["Overheat", "Vibration"],
        "failure_downtime_range": (120, 480),  # worst downtime
    },
    {
        "name": "Pump B",
        "type": "pump",
        "serial": "PUMP-B-005",
        "in_service_date": date(2024, 3, 5),
        "notes": "Cooling water circulation pump. Well-maintained.",
        "failure_pattern": "wearout",         # β ≈ 2.0
        "n_exposures": 50,
        "hours_range": (80, 140),
        "cycles_per_hour": (3.0, 7.0),
        "n_failures": 4,                     # BEST performer (fewest failures)
        "n_maintenance": 8,                  # heavily maintained
        "n_inspections": 6,
        "dominant_modes": ["Bearing wear"],
        "secondary_modes": ["Seal leak"],
        "failure_downtime_range": (20, 90),   # low severity (quick repairs)
    },
    {
        "name": "Pump C",
        "type": "pump",
        "serial": "PUMP-C-006",
        "in_service_date": date(2024, 7, 12),
        "notes": "Process feed pump, moderate duty cycle.",
        "failure_pattern": "random",
        "n_exposures": 45,
        "hours_range": (65, 125),
        "cycles_per_hour": (4.0, 9.0),
        "n_failures": 7,
        "n_maintenance": 4,
        "n_inspections": 3,
        "dominant_modes": ["Seal leak", "Overheat"],
        "secondary_modes": ["Electrical fault"],
        "failure_downtime_range": (45, 210),
    },
    # ---------- Conveyors ----------
    {
        "name": "Conveyor A",
        "type": "conveyor",
        "serial": "CONV-A-007",
        "in_service_date": date(2024, 2, 1),
        "notes": "Main production belt conveyor, 200 m length.",
        "failure_pattern": "wearout",
        "n_exposures": 50,
        "hours_range": (90, 160),
        "cycles_per_hour": (0.3, 0.8),       # low cycling (continuous belt)
        "n_failures": 6,
        "n_maintenance": 5,
        "n_inspections": 4,
        "dominant_modes": ["Belt mistrack", "Drive chain wear"],
        "secondary_modes": ["Motor burnout"],
        "failure_downtime_range": (60, 300),
    },
    {
        "name": "Conveyor B",
        "type": "conveyor",
        "serial": "CONV-B-008",
        "in_service_date": date(2024, 5, 18),
        "notes": "Packaging line conveyor, frequent vibration alarms.",
        "failure_pattern": "wearout",
        "n_exposures": 48,
        "hours_range": (70, 130),
        "cycles_per_hour": (0.5, 1.2),
        "n_failures": 11,                    # second-worst performer
        "n_maintenance": 3,
        "n_inspections": 2,
        "dominant_modes": ["Vibration", "Belt mistrack"],
        "secondary_modes": ["Drive chain wear", "Electrical fault"],
        "failure_downtime_range": (90, 420),
    },
    # ---------- Fans ----------
    {
        "name": "Exhaust Fan A",
        "type": "fan",
        "serial": "FAN-A-009",
        "in_service_date": date(2024, 4, 10),
        "notes": "Process exhaust fan, 50 HP direct-drive.",
        "failure_pattern": "random",
        "n_exposures": 52,
        "hours_range": (100, 168),            # near-continuous
        "cycles_per_hour": (0.1, 0.3),        # minimal cycling
        "n_failures": 5,
        "n_maintenance": 5,
        "n_inspections": 5,
        "dominant_modes": ["Vibration", "Bearing wear"],
        "secondary_modes": ["Electrical fault"],
        "failure_downtime_range": (30, 180),
    },
    {
        "name": "Supply Fan B",
        "type": "fan",
        "serial": "FAN-B-010",
        "in_service_date": date(2025, 1, 8),
        "notes": "HVAC supply fan, relatively new unit.",
        "failure_pattern": "infant",
        "n_exposures": 30,
        "hours_range": (100, 168),
        "cycles_per_hour": (0.1, 0.4),
        "n_failures": 6,
        "n_maintenance": 2,
        "n_inspections": 2,
        "dominant_modes": ["Electrical fault", "Vibration"],
        "secondary_modes": ["Bearing wear"],
        "failure_downtime_range": (15, 120),
    },
]

# A complete catalogue of failure modes across all equipment types
FAILURE_MODE_DEFS: list[dict] = [
    {"name": "Seal leak",         "category": "mechanical"},
    {"name": "Bearing wear",      "category": "mechanical"},
    {"name": "Overheat",          "category": "thermal"},
    {"name": "Vibration",         "category": "mechanical"},
    {"name": "Electrical fault",  "category": "electrical"},
    {"name": "Belt mistrack",     "category": "mechanical"},
    {"name": "Drive chain wear",  "category": "mechanical"},
    {"name": "Motor burnout",     "category": "electrical"},
]

# Parts catalogue — including conveyor-specific parts
PART_DEFS: list[dict] = [
    {"name": "Bearing",        "part_number": "BRG-100"},
    {"name": "Mechanical Seal", "part_number": "SEAL-200"},
    {"name": "Motor",          "part_number": "MTR-300"},
    {"name": "Coupling",       "part_number": "COUP-400"},
    {"name": "Belt Section",   "part_number": "BELT-500"},
    {"name": "Drive Chain",    "part_number": "CHAIN-600"},
    {"name": "Contactor",      "part_number": "ELEC-700"},
]

# Mapping from failure mode → most likely root cause, corrective action, part replaced
MODE_DETAILS: dict[str, dict] = {
    "Seal leak": {
        "root_causes": ["shaft run-out", "dry running", "chemical attack on elastomer", "installation damage"],
        "actions": ["replace mechanical seal", "replace seal and realign shaft", "upgrade seal material"],
        "parts": ["Mechanical Seal"],
    },
    "Bearing wear": {
        "root_causes": ["lubrication starvation", "contaminated grease", "excessive load", "normal end-of-life wear"],
        "actions": ["replace bearing and re-grease", "replace bearing and improve lube schedule", "replace bearing assembly"],
        "parts": ["Bearing"],
    },
    "Overheat": {
        "root_causes": ["blocked cooling fins", "ambient temperature exceedance", "excessive friction", "overload condition"],
        "actions": ["clean cooling system and inspect", "replace thermal paste and verify airflow", "derate operation"],
        "parts": ["Motor", "Coupling"],
    },
    "Vibration": {
        "root_causes": ["unbalance", "misalignment", "loose foundation bolts", "resonance at operating speed"],
        "actions": ["dynamic balance and realign", "torque foundation bolts and realign", "install vibration dampers"],
        "parts": ["Bearing", "Coupling"],
    },
    "Electrical fault": {
        "root_causes": ["insulation breakdown", "loose terminal connection", "VFD parameter drift", "power surge"],
        "actions": ["replace contactor and re-terminate", "replace motor winding", "reconfigure VFD and add surge protection"],
        "parts": ["Contactor", "Motor"],
    },
    "Belt mistrack": {
        "root_causes": ["idler roller seized", "uneven load distribution", "belt splice failure", "frame misalignment"],
        "actions": ["replace tracking idler", "realign frame and re-tension belt", "replace belt section"],
        "parts": ["Belt Section"],
    },
    "Drive chain wear": {
        "root_causes": ["chain elongation beyond 3%", "sprocket tooth wear", "inadequate lubrication"],
        "actions": ["replace chain and sprocket set", "replace chain section and re-lube"],
        "parts": ["Drive Chain"],
    },
    "Motor burnout": {
        "root_causes": ["stall condition", "phase imbalance", "bearing seizure causing rotor lock"],
        "actions": ["replace motor", "replace motor and add phase monitor"],
        "parts": ["Motor"],
    },
}


def _clear_existing(session: Session) -> None:
    """Wipe existing rows so demo seeding is repeatable."""
    for model in (EventFailureDetail, Event, ExposureLog, PartInstall, Part, FailureMode, Asset):
        session.exec(delete(model))
    session.commit()


def _generate_failure_indices(
    n_exposures: int,
    n_failures: int,
    pattern: str,
) -> list[int]:
    """Pick exposure-segment indices for failures to produce the desired Weibull shape.

    * wearout  → failures concentrated in later segments (produces β > 1.5)
    * random   → uniformly distributed (produces β ≈ 1.0)
    * infant   → failures concentrated in early segments (produces β < 0.9)
    """
    # Keep indices away from the very first and last 2 segments
    lo, hi = 2, n_exposures - 2
    pool = list(range(lo, hi))

    if pattern == "wearout":
        # Weight later indices much more heavily
        weights = [(i - lo + 1) ** 2.5 for i in pool]
    elif pattern == "infant":
        # Weight early indices more heavily
        weights = [(hi - i) ** 2.5 for i in pool]
    else:  # random
        weights = [1.0] * len(pool)

    total_w = sum(weights)
    probs = [w / total_w for w in weights]

    chosen: list[int] = []
    remaining_pool = list(pool)
    remaining_probs = list(probs)

    for _ in range(min(n_failures, len(remaining_pool))):
        r = random.random()
        cumulative = 0.0
        for j, (idx, p) in enumerate(zip(remaining_pool, remaining_probs)):
            cumulative += p
            if r <= cumulative:
                chosen.append(idx)
                remaining_pool.pop(j)
                remaining_probs.pop(j)
                # Renormalize
                total_p = sum(remaining_probs)
                if total_p > 0:
                    remaining_probs = [pp / total_p for pp in remaining_probs]
                break

    chosen.sort()
    return chosen


def _pick_maintenance_indices(
    n_exposures: int,
    n_maintenance: int,
    failure_indices: list[int],
) -> list[int]:
    """Place maintenance events logically — some before failures (preventive)
    and some after (corrective follow-up)."""
    candidates = set(range(2, n_exposures - 1)) - set(failure_indices)
    chosen: list[int] = []

    # Place ~40 % of maintenance just before a failure (preventive)
    n_preventive = max(1, int(n_maintenance * 0.4))
    for fidx in failure_indices[:n_preventive]:
        before = fidx - 1
        if before in candidates:
            chosen.append(before)
            candidates.discard(before)

    # Fill remaining from general pool
    remaining = n_maintenance - len(chosen)
    if remaining > 0 and candidates:
        chosen.extend(random.sample(sorted(candidates), min(remaining, len(candidates))))

    chosen.sort()
    return chosen


def _pick_inspection_indices(
    n_exposures: int,
    n_inspections: int,
    used_indices: set[int],
) -> list[int]:
    """Place inspections at roughly even intervals through the operating window."""
    candidates = sorted(set(range(3, n_exposures - 1)) - used_indices)
    if not candidates or n_inspections == 0:
        return []
    step = max(1, len(candidates) // n_inspections)
    chosen = candidates[::step][:n_inspections]
    return sorted(chosen)


def seed_demo_dataset(session: Session, reset: bool = True) -> Dict[str, int]:
    """Create a comprehensive, reproducible demo dataset.

    Exercises every analytical feature in RELIABASE:
    - 10 assets with differentiated failure behaviours
    - 8 failure modes with correlated root causes / actions / part replacements
    - Wear-out, random, and infant-mortality Weibull patterns
    - Clear bad-actor ranking (Pump A is worst, Pump B is best)
    - Enough failure intervals for stable Weibull, B-life, repair effectiveness
    - Meaningful RPN differentiation via varying severity and occurrence
    - Varying cycle rates per equipment type for OEE / performance rate
    - Part install/remove lifecycle tracking
    """
    if reset:
        _clear_existing(session)

    random.seed(42)
    now = datetime.now(timezone.utc)

    # ── 1. Create failure modes ─────────────────────────────────────────
    fm_map: dict[str, FailureMode] = {}
    for fmd in FAILURE_MODE_DEFS:
        fm = FailureMode(name=fmd["name"], category=fmd["category"])
        session.add(fm)
        session.flush()
        fm_map[fm.name] = fm
    session.commit()

    # ── 2. Create parts ─────────────────────────────────────────────────
    part_map: dict[str, Part] = {}
    for pd in PART_DEFS:
        p = Part(name=pd["name"], part_number=pd["part_number"])
        session.add(p)
        session.flush()
        part_map[p.name] = p
    session.commit()

    # ── 3. Create assets ────────────────────────────────────────────────
    assets: list[Asset] = []
    for prof in ASSET_PROFILES:
        a = Asset(
            name=prof["name"],
            type=prof["type"],
            serial=prof["serial"],
            in_service_date=prof["in_service_date"],
            notes=prof["notes"],
        )
        session.add(a)
        session.flush()
        assets.append(a)
    session.commit()

    # ── 4. Generate exposures, events, details, installs per asset ──────
    all_exposures: list[ExposureLog] = []
    all_events: list[Event] = []
    all_details: list[EventFailureDetail] = []
    all_installs: list[PartInstall] = []

    for asset, prof in zip(assets, ASSET_PROFILES):
        n_exp = prof["n_exposures"]
        hrs_lo, hrs_hi = prof["hours_range"]
        cyc_lo, cyc_hi = prof["cycles_per_hour"]

        # --- Exposure logs spanning ~365 days back from now ---
        start = now - timedelta(days=365)
        asset_exposures: list[ExposureLog] = []
        for seg_idx in range(n_exp):
            duration_hours = random.uniform(hrs_lo, hrs_hi)
            # Vary cycles/hour per segment — gives OEE performance rate diversity
            cycles = duration_hours * random.uniform(cyc_lo, cyc_hi)
            end = start + timedelta(hours=duration_hours)
            asset_exposures.append(
                ExposureLog(
                    asset_id=asset.id,
                    start_time=start,
                    end_time=end,
                    hours=round(duration_hours, 2),
                    cycles=round(cycles, 1),
                )
            )
            # Gap between shifts (2-12 h)
            start = end + timedelta(hours=random.uniform(2, 12))
        all_exposures.extend(asset_exposures)

        # --- Failure events with pattern-controlled placement ---
        failure_indices = _generate_failure_indices(
            n_exp, prof["n_failures"], prof["failure_pattern"],
        )
        maintenance_indices = _pick_maintenance_indices(
            n_exp, prof["n_maintenance"], failure_indices,
        )
        used = set(failure_indices) | set(maintenance_indices)
        inspection_indices = _pick_inspection_indices(n_exp, prof["n_inspections"], used)

        dt_lo, dt_hi = prof["failure_downtime_range"]

        # Failure events
        for i, fidx in enumerate(failure_indices):
            log = asset_exposures[fidx]
            # Downtime increases with wear-out pattern (later failures are worse)
            if prof["failure_pattern"] == "wearout":
                severity_fraction = (i + 1) / len(failure_indices)
                downtime = dt_lo + (dt_hi - dt_lo) * severity_fraction * random.uniform(0.7, 1.0)
            elif prof["failure_pattern"] == "infant":
                severity_fraction = 1.0 - (i / len(failure_indices))
                downtime = dt_lo + (dt_hi - dt_lo) * severity_fraction * random.uniform(0.6, 1.0)
            else:
                downtime = random.uniform(dt_lo, dt_hi)

            # Pick failure mode — weighted toward dominant modes
            if random.random() < 0.7:
                mode_name = random.choice(prof["dominant_modes"])
            else:
                mode_name = random.choice(prof.get("secondary_modes", prof["dominant_modes"]))

            fm = fm_map[mode_name]
            detail_info = MODE_DETAILS[mode_name]

            evt = Event(
                asset_id=asset.id,
                timestamp=log.end_time,
                event_type="failure",
                downtime_minutes=round(downtime, 1),
                description=f"{mode_name} on {asset.name}: {random.choice(detail_info['root_causes'])}",
            )
            session.add(evt)
            session.flush()
            all_events.append(evt)

            # Failure detail — correlated root cause, action, part
            efd = EventFailureDetail(
                event_id=evt.id,
                failure_mode_id=fm.id,
                root_cause=random.choice(detail_info["root_causes"]),
                corrective_action=random.choice(detail_info["actions"]),
                part_replaced=random.choice(detail_info["parts"]),
            )
            all_details.append(efd)

        # Maintenance events
        for midx in maintenance_indices:
            log = asset_exposures[midx]
            evt = Event(
                asset_id=asset.id,
                timestamp=log.end_time,
                event_type="maintenance",
                downtime_minutes=round(random.uniform(15, 90), 1),
                description=f"Planned preventive maintenance on {asset.name}",
            )
            session.add(evt)
            session.flush()
            all_events.append(evt)

        # Inspection events
        for iidx in inspection_indices:
            log = asset_exposures[iidx]
            evt = Event(
                asset_id=asset.id,
                timestamp=log.end_time,
                event_type="inspection",
                downtime_minutes=round(random.uniform(5, 30), 1),
                description=f"Routine inspection on {asset.name}",
            )
            session.add(evt)
            session.flush()
            all_events.append(evt)

        # --- Part installs (lifecycle tracking) ---
        # Determine which parts are relevant to this asset type
        relevant_parts: list[str] = set()
        for mode_name in prof["dominant_modes"] + prof.get("secondary_modes", []):
            for pname in MODE_DETAILS[mode_name]["parts"]:
                relevant_parts.add(pname)
        # Always include Bearing and Coupling as universal parts
        relevant_parts.update(["Bearing", "Coupling"])

        for pname in sorted(relevant_parts):
            if pname not in part_map:
                continue
            part = part_map[pname]
            # Create 1-3 install records per relevant part (showing lifecycle)
            n_installs = random.randint(1, 3)
            install_cursor = now - timedelta(days=random.randint(200, 350))
            for _ in range(n_installs):
                life_days = random.randint(30, 120)
                remove_time = install_cursor + timedelta(days=life_days)
                # Last install may still be active (no remove_time)
                is_last = (_ == n_installs - 1)
                all_installs.append(
                    PartInstall(
                        asset_id=asset.id,
                        part_id=part.id,
                        install_time=install_cursor,
                        remove_time=None if is_last and random.random() > 0.3 else remove_time,
                    )
                )
                install_cursor = remove_time + timedelta(hours=random.uniform(2, 48))

    session.add_all(all_exposures)
    session.add_all(all_details)
    session.add_all(all_installs)
    session.commit()

    return {
        "assets": len(assets),
        "exposures": len(all_exposures),
        "events": len(all_events),
        "failure_details": len(all_details),
        "failure_modes": len(fm_map),
        "parts": len(part_map),
        "installs": len(all_installs),
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
        "Demo dataset generated: "
        f"{summary['assets']} assets, {summary['events']} events, "
        f"{summary['exposures']} exposures, {summary['failure_details']} failure details, "
        f"{summary['failure_modes']} failure modes, {summary['parts']} parts, "
        f"{summary['installs']} part installs."
    )
    engine.dispose()


if __name__ == "__main__":
    app()
