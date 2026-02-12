"""Demo service - Dataset seeding operations."""
from __future__ import annotations

from typing import Dict
from sqlmodel import Session, select, func

from reliabase.models import Asset, Event, ExposureLog, FailureMode, EventFailureDetail, Part, PartInstall
from reliabase.seed_demo import seed_demo_dataset, _clear_existing


class DemoService:
    """Service class for demo data operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def seed(self, reset: bool = True) -> Dict:
        """Seed demo data and return counts.
        
        Parameters
        ----------
        reset : bool
            If True, clears existing data before seeding.
            
        Returns
        -------
        dict
            Dictionary with 'created' and 'totals' counts.
        """
        # Get counts before seeding
        before = self._get_counts()
        
        # Seed the data
        summary = seed_demo_dataset(self.session, reset=reset)
        
        # Get counts after seeding
        after = self._get_counts()
        
        # Use the summary from seed_demo_dataset directly for created counts
        created = {
            "assets": summary.get("assets", 0),
            "events": summary.get("events", 0),
            "exposures": summary.get("exposures", 0),
            "failure_modes": summary.get("failure_modes", 0),
            "failure_details": summary.get("failure_details", 0),
            "parts": summary.get("parts", 0),
            "installs": summary.get("installs", 0),
        }
        
        return {
            "created": created,
            "totals": after,
        }
    
    def clear(self) -> Dict[str, int]:
        """Clear all data from the database.
        
        Returns
        -------
        dict
            Counts of records that were deleted.
        """
        before = self._get_counts()
        _clear_existing(self.session)
        return before
    
    def _get_counts(self) -> Dict[str, int]:
        """Get current counts of all data types."""
        return {
            "assets": self.session.exec(select(func.count(Asset.id))).one(),
            "events": self.session.exec(select(func.count(Event.id))).one(),
            "exposures": self.session.exec(select(func.count(ExposureLog.id))).one(),
            "failure_modes": self.session.exec(select(func.count(FailureMode.id))).one(),
            "parts": self.session.exec(select(func.count(Part.id))).one(),
        }
    
    def get_totals(self) -> Dict[str, int]:
        """Get current totals without seeding."""
        return self._get_counts()
