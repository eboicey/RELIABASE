"""Failure mode CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/failure-modes", tags=["failure-modes"])


@router.get("/", response_model=list[schemas.FailureModeRead])
def list_failure_modes(session: SessionDep, offset: int = 0, limit: int = 100):
    items = session.exec(select(models.FailureMode).offset(offset).limit(limit)).all()
    return items


@router.post("/", response_model=schemas.FailureModeRead, status_code=201)
def create_failure_mode(payload: schemas.FailureModeCreate, session: SessionDep):
    item = models.FailureMode(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{fm_id}", response_model=schemas.FailureModeRead)
def get_failure_mode(fm_id: int, session: SessionDep):
    item = session.get(models.FailureMode, fm_id)
    if not item:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    return item


@router.patch("/{fm_id}", response_model=schemas.FailureModeRead)
def update_failure_mode(fm_id: int, payload: schemas.FailureModeUpdate, session: SessionDep):
    item = session.get(models.FailureMode, fm_id)
    if not item:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{fm_id}", status_code=204)
def delete_failure_mode(fm_id: int, session: SessionDep):
    item = session.get(models.FailureMode, fm_id)
    if not item:
        raise HTTPException(status_code=404, detail="Failure mode not found")
    session.delete(item)
    session.commit()
    return None
