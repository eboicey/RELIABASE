"""Event failure detail CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/event-details", tags=["event-details"])


@router.get("/", response_model=list[schemas.EventFailureDetailRead])
def list_event_details(session: SessionDep, offset: int = 0, limit: int = 100, event_id: int | None = None):
    query = select(models.EventFailureDetail)
    if event_id is not None:
        query = query.where(models.EventFailureDetail.event_id == event_id)
    items = session.exec(query.offset(offset).limit(limit)).all()
    return items


@router.post("/", response_model=schemas.EventFailureDetailRead, status_code=201)
def create_event_detail(payload: schemas.EventFailureDetailCreate, session: SessionDep):
    item = models.EventFailureDetail.from_orm(payload)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{detail_id}", response_model=schemas.EventFailureDetailRead)
def get_event_detail(detail_id: int, session: SessionDep):
    item = session.get(models.EventFailureDetail, detail_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event detail not found")
    return item


@router.patch("/{detail_id}", response_model=schemas.EventFailureDetailRead)
def update_event_detail(detail_id: int, payload: schemas.EventFailureDetailUpdate, session: SessionDep):
    item = session.get(models.EventFailureDetail, detail_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event detail not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{detail_id}", status_code=204)
def delete_event_detail(detail_id: int, session: SessionDep):
    item = session.get(models.EventFailureDetail, detail_id)
    if not item:
        raise HTTPException(status_code=404, detail="Event detail not found")
    session.delete(item)
    session.commit()
    return None
