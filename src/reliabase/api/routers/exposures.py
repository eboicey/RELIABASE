"""Exposure log CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/exposures", tags=["exposures"])


@router.get("/", response_model=list[schemas.ExposureLogRead])
def list_exposures(session: SessionDep, offset: int = 0, limit: int = 100, asset_id: int | None = None):
    query = select(models.ExposureLog)
    if asset_id is not None:
        query = query.where(models.ExposureLog.asset_id == asset_id)
    logs = session.exec(query.offset(offset).limit(limit)).all()
    return logs


@router.post("/", response_model=schemas.ExposureLogRead, status_code=201)
def create_exposure(payload: schemas.ExposureLogCreate, session: SessionDep):
    log = models.ExposureLog.from_orm(payload)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.get("/{log_id}", response_model=schemas.ExposureLogRead)
def get_exposure(log_id: int, session: SessionDep):
    log = session.get(models.ExposureLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Exposure not found")
    return log


@router.patch("/{log_id}", response_model=schemas.ExposureLogRead)
def update_exposure(log_id: int, payload: schemas.ExposureLogUpdate, session: SessionDep):
    log = session.get(models.ExposureLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Exposure not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(log, field, value)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.delete("/{log_id}", status_code=204)
def delete_exposure(log_id: int, session: SessionDep):
    log = session.get(models.ExposureLog, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Exposure not found")
    session.delete(log)
    session.commit()
    return None
