"""Pydantic/SQLModel schemas for API IO."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel


class AssetBase(SQLModel):
    name: str
    type: Optional[str] = None
    serial: Optional[str] = None
    in_service_date: Optional[date] = None
    notes: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetRead(AssetBase):
    id: int


class AssetUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[str] = None
    serial: Optional[str] = None
    in_service_date: Optional[date] = None
    notes: Optional[str] = None


class ExposureLogBase(SQLModel):
    asset_id: int
    start_time: datetime
    end_time: datetime
    hours: float = 0.0
    cycles: float = 0.0


class ExposureLogCreate(ExposureLogBase):
    pass


class ExposureLogRead(ExposureLogBase):
    id: int


class ExposureLogUpdate(SQLModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    hours: Optional[float] = None
    cycles: Optional[float] = None


class EventBase(SQLModel):
    asset_id: int
    timestamp: datetime
    event_type: str
    downtime_minutes: Optional[float] = 0.0
    description: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: int


class EventUpdate(SQLModel):
    timestamp: Optional[datetime] = None
    event_type: Optional[str] = None
    downtime_minutes: Optional[float] = None
    description: Optional[str] = None


class FailureModeBase(SQLModel):
    name: str
    category: Optional[str] = None


class FailureModeCreate(FailureModeBase):
    pass


class FailureModeRead(FailureModeBase):
    id: int


class FailureModeUpdate(SQLModel):
    name: Optional[str] = None
    category: Optional[str] = None


class EventFailureDetailBase(SQLModel):
    event_id: int
    failure_mode_id: int
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    part_replaced: Optional[str] = None


class EventFailureDetailCreate(EventFailureDetailBase):
    pass


class EventFailureDetailRead(EventFailureDetailBase):
    id: int


class EventFailureDetailUpdate(SQLModel):
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    part_replaced: Optional[str] = None


class PartBase(SQLModel):
    name: str
    part_number: Optional[str] = None


class PartCreate(PartBase):
    pass


class PartRead(PartBase):
    id: int


class PartUpdate(SQLModel):
    name: Optional[str] = None
    part_number: Optional[str] = None


class PartInstallBase(SQLModel):
    asset_id: int
    install_time: datetime
    remove_time: Optional[datetime] = None


class PartInstallCreate(PartInstallBase):
    pass


class PartInstallRead(PartInstallBase):
    id: int
    part_id: int


class PartInstallUpdate(SQLModel):
    install_time: Optional[datetime] = None
    remove_time: Optional[datetime] = None
