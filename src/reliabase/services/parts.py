"""Part service - CRUD operations for parts and part installs."""
from __future__ import annotations

from typing import Optional, List
from sqlmodel import Session, select

from reliabase.models import Part, PartInstall
from reliabase.schemas import PartCreate, PartUpdate, PartInstallCreate, PartInstallUpdate


class PartService:
    """Service class for Part and PartInstall operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    # Part operations
    def list_parts(self, offset: int = 0, limit: int = 100) -> List[Part]:
        """List all parts with pagination."""
        return list(self.session.exec(select(Part).offset(offset).limit(limit)).all())
    
    def get_part(self, part_id: int) -> Optional[Part]:
        """Get a single part by ID."""
        return self.session.get(Part, part_id)
    
    def create_part(self, data: PartCreate) -> Part:
        """Create a new part."""
        part = Part(**data.model_dump())
        self.session.add(part)
        self.session.commit()
        self.session.refresh(part)
        return part
    
    def update_part(self, part_id: int, data: PartUpdate) -> Optional[Part]:
        """Update an existing part."""
        part = self.session.get(Part, part_id)
        if not part:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(part, field, value)
        self.session.add(part)
        self.session.commit()
        self.session.refresh(part)
        return part
    
    def delete_part(self, part_id: int) -> bool:
        """Delete a part. Returns True if deleted, False if not found."""
        part = self.session.get(Part, part_id)
        if not part:
            return False
        self.session.delete(part)
        self.session.commit()
        return True
    
    # Part Install operations
    def list_installs(self, part_id: Optional[int] = None, asset_id: Optional[int] = None, 
                      offset: int = 0, limit: int = 100) -> List[PartInstall]:
        """List part installs with optional filtering."""
        query = select(PartInstall)
        if part_id is not None:
            query = query.where(PartInstall.part_id == part_id)
        if asset_id is not None:
            query = query.where(PartInstall.asset_id == asset_id)
        return list(self.session.exec(query.offset(offset).limit(limit)).all())
    
    def get_install(self, install_id: int) -> Optional[PartInstall]:
        """Get a single part install by ID."""
        return self.session.get(PartInstall, install_id)
    
    def create_install(self, part_id: int, data: PartInstallCreate) -> PartInstall:
        """Create a new part install."""
        install = PartInstall(part_id=part_id, **data.model_dump())
        self.session.add(install)
        self.session.commit()
        self.session.refresh(install)
        return install
    
    def update_install(self, install_id: int, data: PartInstallUpdate) -> Optional[PartInstall]:
        """Update an existing part install."""
        install = self.session.get(PartInstall, install_id)
        if not install:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(install, field, value)
        self.session.add(install)
        self.session.commit()
        self.session.refresh(install)
        return install
    
    def delete_install(self, install_id: int) -> bool:
        """Delete a part install. Returns True if deleted, False if not found."""
        install = self.session.get(PartInstall, install_id)
        if not install:
            return False
        self.session.delete(install)
        self.session.commit()
        return True
