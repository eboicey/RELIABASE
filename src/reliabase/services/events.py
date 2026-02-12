"""Event service - CRUD operations for events."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import Event
from reliabase.schemas import EventCreate, EventUpdate


class EventService:
    """Service class for Event operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def list(self, offset: int = 0, limit: int = 100, asset_id: Optional[int] = None) -> List[Event]:
        """List events with optional filtering by asset."""
        query = select(Event)
        if asset_id is not None:
            query = query.where(Event.asset_id == asset_id)
        return list(self.session.exec(query.offset(offset).limit(limit)).all())
    
    def get(self, event_id: int) -> Optional[Event]:
        """Get a single event by ID."""
        return self.session.get(Event, event_id)
    
    def create(self, data: EventCreate) -> Event:
        """Create a new event."""
        event = Event(**data.model_dump())
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
    
    def update(self, event_id: int, data: EventUpdate) -> Optional[Event]:
        """Update an existing event."""
        event = self.session.get(Event, event_id)
        if not event:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)
        self.session.add(event)
        self.session.commit()
        self.session.refresh(event)
        return event
    
    def delete(self, event_id: int) -> bool:
        """Delete an event. Returns True if deleted, False if not found."""
        event = self.session.get(Event, event_id)
        if not event:
            return False
        self.session.delete(event)
        self.session.commit()
        return True
