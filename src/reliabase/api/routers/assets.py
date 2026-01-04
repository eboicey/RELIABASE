"""Asset CRUD endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from reliabase import models, schemas
from reliabase.api.deps import SessionDep

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/", response_model=list[schemas.AssetRead])
def list_assets(session: SessionDep, offset: int = 0, limit: int = 100):
    assets = session.exec(select(models.Asset).offset(offset).limit(limit)).all()
    return assets


@router.post("/", response_model=schemas.AssetRead, status_code=201)
def create_asset(payload: schemas.AssetCreate, session: SessionDep):
    asset = models.Asset(**payload.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=schemas.AssetRead)
def get_asset(asset_id: int, session: SessionDep):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}", response_model=schemas.AssetRead)
def update_asset(asset_id: int, payload: schemas.AssetUpdate, session: SessionDep):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, session: SessionDep):
    asset = session.get(models.Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    session.delete(asset)
    session.commit()
    return None
