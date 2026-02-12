"""Exposure service - CRUD operations for exposure logs."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import ExposureLog
from reliabase.schemas import ExposureLogCreate, ExposureLogUpdate


class ExposureService:
    """Service class for ExposureLog operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def list(self, offset: int = 0, limit: int = 100, asset_id: Optional[int] = None) -> List[ExposureLog]:
        """List exposure logs with optional filtering by asset."""
        query = select(ExposureLog)
        if asset_id is not None:
            query = query.where(ExposureLog.asset_id == asset_id)
        return list(self.session.exec(query.offset(offset).limit(limit)).all())
    
    def get(self, exposure_id: int) -> Optional[ExposureLog]:
        """Get a single exposure log by ID."""
        return self.session.get(ExposureLog, exposure_id)
    
    def create(self, data: ExposureLogCreate) -> ExposureLog:
        """Create a new exposure log."""
        # Auto-calculate hours if not provided
        data_dict = data.model_dump()
        if not data_dict.get("hours") or data_dict["hours"] == 0:
            delta = data.end_time - data.start_time
            data_dict["hours"] = delta.total_seconds() / 3600
        
        exposure = ExposureLog(**data_dict)
        self.session.add(exposure)
        self.session.commit()
        self.session.refresh(exposure)
        return exposure
    
    def update(self, exposure_id: int, data: ExposureLogUpdate) -> Optional[ExposureLog]:
        """Update an existing exposure log."""
        exposure = self.session.get(ExposureLog, exposure_id)
        if not exposure:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exposure, field, value)
        self.session.add(exposure)
        self.session.commit()
        self.session.refresh(exposure)
        return exposure
    
    def delete(self, exposure_id: int) -> bool:
        """Delete an exposure log. Returns True if deleted, False if not found."""
        exposure = self.session.get(ExposureLog, exposure_id)
        if not exposure:
            return False
        self.session.delete(exposure)
        self.session.commit()
        return True
