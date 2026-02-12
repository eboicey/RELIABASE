"""Event Detail service - CRUD operations for event failure details."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import EventFailureDetail
from reliabase.schemas import EventFailureDetailCreate, EventFailureDetailUpdate


class EventDetailService:
    """Service class for EventFailureDetail operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def list(self, offset: int = 0, limit: int = 100, event_id: Optional[int] = None) -> List[EventFailureDetail]:
        """List event details with optional filtering by event."""
        query = select(EventFailureDetail)
        if event_id is not None:
            query = query.where(EventFailureDetail.event_id == event_id)
        return list(self.session.exec(query.offset(offset).limit(limit)).all())
    
    def get(self, detail_id: int) -> Optional[EventFailureDetail]:
        """Get a single event detail by ID."""
        return self.session.get(EventFailureDetail, detail_id)
    
    def create(self, data: EventFailureDetailCreate) -> EventFailureDetail:
        """Create a new event failure detail."""
        detail = EventFailureDetail(**data.model_dump())
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail
    
    def update(self, detail_id: int, data: EventFailureDetailUpdate) -> Optional[EventFailureDetail]:
        """Update an existing event detail."""
        detail = self.session.get(EventFailureDetail, detail_id)
        if not detail:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(detail, field, value)
        self.session.add(detail)
        self.session.commit()
        self.session.refresh(detail)
        return detail
    
    def delete(self, detail_id: int) -> bool:
        """Delete an event detail. Returns True if deleted, False if not found."""
        detail = self.session.get(EventFailureDetail, detail_id)
        if not detail:
            return False
        self.session.delete(detail)
        self.session.commit()
        return True
