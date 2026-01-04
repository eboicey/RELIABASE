"""Demo utilities (seeding endpoints)."""
from __future__ import annotations

from fastapi import APIRouter, Body
from sqlalchemy import func
from sqlmodel import Session, select

from reliabase import models
from reliabase.api.deps import SessionDep
from reliabase.seed_demo import seed_demo_dataset

router = APIRouter(prefix="/demo", tags=["demo"])


def _count(session: Session, model) -> int:
    return int(session.exec(select(func.count(model.id))).one())


@router.post("/seed")
def seed_demo(session: SessionDep, reset: bool = Body(True, embed=True)):
    """Seed the database with demo data. Optionally reset existing records."""
    summary = seed_demo_dataset(session, reset=reset)
    totals = {
        "assets": _count(session, models.Asset),
        "exposures": _count(session, models.ExposureLog),
        "events": _count(session, models.Event),
        "failure_details": _count(session, models.EventFailureDetail),
        "parts": _count(session, models.Part),
        "installs": _count(session, models.PartInstall),
    }
    return {"status": "ok", "reset": reset, "created": summary, "totals": totals}
