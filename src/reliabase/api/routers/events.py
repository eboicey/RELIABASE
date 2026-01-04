"""Event CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

ALLOWED_EVENT_TYPES = {"failure", "maintenance", "inspection"}

router = APIRouter(prefix="/events", tags=["events"])


def _validate_event_type(value: str) -> str:
    normalized = value.lower()
    if normalized not in ALLOWED_EVENT_TYPES:
        raise HTTPException(status_code=400, detail=f"event_type must be one of {sorted(ALLOWED_EVENT_TYPES)}")
    return normalized


@router.get("/", response_model=list[schemas.EventRead])
def list_events(session: SessionDep, offset: int = 0, limit: int = 100, asset_id: int | None = None):
    query = select(models.Event)
    if asset_id is not None:
        query = query.where(models.Event.asset_id == asset_id)
    events = session.exec(query.order_by(models.Event.timestamp).offset(offset).limit(limit)).all()
    return events


@router.post("/", response_model=schemas.EventRead, status_code=201)
def create_event(payload: schemas.EventCreate, session: SessionDep):
    event_type = _validate_event_type(payload.event_type)
    data = payload.model_dump()
    data["event_type"] = event_type
    event = models.Event(**data)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/{event_id}", response_model=schemas.EventRead)
def get_event(event_id: int, session: SessionDep):
    event = session.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=schemas.EventRead)
def update_event(event_id: int, payload: schemas.EventUpdate, session: SessionDep):
    event = session.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    data = payload.model_dump(exclude_unset=True)
    if "event_type" in data:
        data["event_type"] = _validate_event_type(data["event_type"])
    for field, value in data.items():
        setattr(event, field, value)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, session: SessionDep):
    event = session.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    session.delete(event)
    session.commit()
    return None
