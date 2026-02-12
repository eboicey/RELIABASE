"""Asset service - CRUD operations for assets."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import Asset
from reliabase.schemas import AssetCreate, AssetUpdate


class AssetService:
    """Service class for Asset operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def list(self, offset: int = 0, limit: int = 100) -> List[Asset]:
        """List all assets with pagination."""
        return list(self.session.exec(select(Asset).offset(offset).limit(limit)).all())
    
    def get(self, asset_id: int) -> Optional[Asset]:
        """Get a single asset by ID."""
        return self.session.get(Asset, asset_id)
    
    def create(self, data: AssetCreate) -> Asset:
        """Create a new asset."""
        asset = Asset(**data.model_dump())
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset
    
    def update(self, asset_id: int, data: AssetUpdate) -> Optional[Asset]:
        """Update an existing asset."""
        asset = self.session.get(Asset, asset_id)
        if not asset:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(asset, field, value)
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset
    
    def delete(self, asset_id: int) -> bool:
        """Delete an asset. Returns True if deleted, False if not found."""
        asset = self.session.get(Asset, asset_id)
        if not asset:
            return False
        self.session.delete(asset)
        self.session.commit()
        return True
