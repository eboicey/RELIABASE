"""Failure Mode service - CRUD operations for failure modes."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import FailureMode
from reliabase.schemas import FailureModeCreate, FailureModeUpdate


class FailureModeService:
    """Service class for FailureMode operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def list(self, offset: int = 0, limit: int = 100) -> List[FailureMode]:
        """List all failure modes with pagination."""
        return list(self.session.exec(select(FailureMode).offset(offset).limit(limit)).all())
    
    def get(self, mode_id: int) -> Optional[FailureMode]:
        """Get a single failure mode by ID."""
        return self.session.get(FailureMode, mode_id)
    
    def create(self, data: FailureModeCreate) -> FailureMode:
        """Create a new failure mode."""
        mode = FailureMode(**data.model_dump())
        self.session.add(mode)
        self.session.commit()
        self.session.refresh(mode)
        return mode
    
    def update(self, mode_id: int, data: FailureModeUpdate) -> Optional[FailureMode]:
        """Update an existing failure mode."""
        mode = self.session.get(FailureMode, mode_id)
        if not mode:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(mode, field, value)
        self.session.add(mode)
        self.session.commit()
        self.session.refresh(mode)
        return mode
    
    def delete(self, mode_id: int) -> bool:
        """Delete a failure mode. Returns True if deleted, False if not found."""
        mode = self.session.get(FailureMode, mode_id)
        if not mode:
            return False
        self.session.delete(mode)
        self.session.commit()
        return True
