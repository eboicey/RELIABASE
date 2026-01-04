"""Part and install CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("/", response_model=list[schemas.PartRead])
def list_parts(session: SessionDep, offset: int = 0, limit: int = 100):
    items = session.exec(select(models.Part).offset(offset).limit(limit)).all()
    return items


@router.post("/", response_model=schemas.PartRead, status_code=201)
def create_part(payload: schemas.PartCreate, session: SessionDep):
    item = models.Part(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.get("/{part_id}", response_model=schemas.PartRead)
def get_part(part_id: int, session: SessionDep):
    item = session.get(models.Part, part_id)
    if not item:
        raise HTTPException(status_code=404, detail="Part not found")
    return item


@router.patch("/{part_id}", response_model=schemas.PartRead)
def update_part(part_id: int, payload: schemas.PartUpdate, session: SessionDep):
    item = session.get(models.Part, part_id)
    if not item:
        raise HTTPException(status_code=404, detail="Part not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{part_id}", status_code=204)
def delete_part(part_id: int, session: SessionDep):
    item = session.get(models.Part, part_id)
    if not item:
        raise HTTPException(status_code=404, detail="Part not found")
    session.delete(item)
    session.commit()
    return None


# Part installs

@router.get("/{part_id}/installs", response_model=list[schemas.PartInstallRead])
def list_part_installs(part_id: int, session: SessionDep):
    query = select(models.PartInstall).where(models.PartInstall.part_id == part_id)
    return session.exec(query).all()


def _validate_install_times(install_time, remove_time):
    if remove_time is not None:
        base_install = install_time.replace(tzinfo=None) if getattr(install_time, "tzinfo", None) else install_time
        base_remove = remove_time.replace(tzinfo=None) if getattr(remove_time, "tzinfo", None) else remove_time
        if base_remove <= base_install:
            raise HTTPException(status_code=400, detail="remove_time must be after install_time")


@router.post("/{part_id}/installs", response_model=schemas.PartInstallRead, status_code=201)
def create_part_install(part_id: int, payload: schemas.PartInstallCreate, session: SessionDep):
    _validate_install_times(payload.install_time, payload.remove_time)
    data = payload.model_dump()
    data["part_id"] = part_id
    install = models.PartInstall(**data)
    session.add(install)
    session.commit()
    session.refresh(install)
    return install


@router.patch("/installs/{install_id}", response_model=schemas.PartInstallRead)
def update_part_install(install_id: int, payload: schemas.PartInstallUpdate, session: SessionDep):
    install = session.get(models.PartInstall, install_id)
    if not install:
        raise HTTPException(status_code=404, detail="Part install not found")
    data = payload.model_dump(exclude_unset=True)
    new_install_time = data.get("install_time", install.install_time)
    new_remove_time = data.get("remove_time", install.remove_time)
    _validate_install_times(new_install_time, new_remove_time)
    install.install_time = new_install_time
    install.remove_time = new_remove_time
    session.add(install)
    session.commit()
    session.refresh(install)
    return install


@router.delete("/installs/{install_id}", status_code=204)
def delete_part_install(install_id: int, session: SessionDep):
    install = session.get(models.PartInstall, install_id)
    if not install:
        raise HTTPException(status_code=404, detail="Part install not found")
    session.delete(install)
    session.commit()
    return None
