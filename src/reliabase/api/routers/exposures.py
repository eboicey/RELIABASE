"""Exposure log CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/exposures", tags=["exposures"])


def _validate_interval(start, end):
    if end <= start:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")


def _normalize_dt(dt):
    return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt


def _compute_hours(payload: schemas.ExposureLogBase) -> float:
    if payload.hours and payload.hours > 0:
        return payload.hours
    return (payload.end_time - payload.start_time).total_seconds() / 3600


def _check_overlap(session: Session, asset_id: int, start, end, exclude_id: int | None = None):
    query = select(models.ExposureLog).where(
        models.ExposureLog.asset_id == asset_id,
        models.ExposureLog.start_time < end,
        models.ExposureLog.end_time > start,
    )
    if exclude_id:
        query = query.where(models.ExposureLog.id != exclude_id)
    existing = session.exec(query).first()
    if existing:
        raise HTTPException(status_code=400, detail="Exposure interval overlaps existing record")


@router.get("/", response_model=list[schemas.ExposureLogRead])
def list_exposures(session: SessionDep, offset: int = 0, limit: int = 100, asset_id: int | None = None):
    query = select(models.ExposureLog)
    if asset_id is not None:
        query = query.where(models.ExposureLog.asset_id == asset_id)
    logs = session.exec(query.offset(offset).limit(limit)).all()
    return logs


@router.post("/", response_model=schemas.ExposureLogRead, status_code=201)
def create_exposure(payload: schemas.ExposureLogCreate, session: SessionDep):
    start = _normalize_dt(payload.start_time)
    end = _normalize_dt(payload.end_time)
    _validate_interval(start, end)
    _check_overlap(session, payload.asset_id, start, end)
    hours = _compute_hours(payload)
    log = models.ExposureLog(**payload.model_dump())
    log.start_time = start
    log.end_time = end
    log.hours = hours
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
    data = payload.model_dump(exclude_unset=True)
    if "start_time" in data or "end_time" in data:
        start = _normalize_dt(data.get("start_time", log.start_time))
        end = _normalize_dt(data.get("end_time", log.end_time))
        _validate_interval(start, end)
        _check_overlap(session, log.asset_id, start, end, exclude_id=log.id)
        log.start_time = start
        log.end_time = end
    if "hours" in data:
        log.hours = data["hours"] if data["hours"] is not None else log.hours
    elif "start_time" in data or "end_time" in data:
        log.hours = (log.end_time - log.start_time).total_seconds() / 3600
    if "cycles" in data:
        log.cycles = data["cycles"] if data["cycles"] is not None else log.cycles
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
