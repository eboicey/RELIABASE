"""Demo service - Dataset seeding operations."""
from __future__ import annotations

from typing import Dict
from sqlmodel import Session, select, func

from reliabase.models import Asset, Event, ExposureLog, FailureMode, EventFailureDetail, Part, PartInstall
from reliabase.seed_demo import seed_demo_dataset


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
        seed_demo_dataset(self.session, reset=reset)
        
        # Get counts after seeding
        after = self._get_counts()
        
        # Calculate created counts
        created = {
            "assets": after["assets"] - (0 if reset else before["assets"]),
            "events": after["events"] - (0 if reset else before["events"]),
            "exposures": after["exposures"] - (0 if reset else before["exposures"]),
            "failure_modes": after["failure_modes"] - (0 if reset else before["failure_modes"]),
            "parts": after["parts"] - (0 if reset else before["parts"]),
        }
        
        return {
            "created": created,
            "totals": after,
        }
    
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
