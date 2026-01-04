"""SQLModel models for RELIABASE core data."""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: Optional[str] = None
    serial: Optional[str] = None
    in_service_date: Optional[date] = None
    notes: Optional[str] = None

    exposure_logs: list["ExposureLog"] = Relationship(back_populates="asset")
    events: list["Event"] = Relationship(back_populates="asset")
    part_installs: list["PartInstall"] = Relationship(back_populates="asset")


class ExposureLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    start_time: datetime
    end_time: datetime
    hours: float = 0.0
    cycles: float = 0.0

    asset: Asset = Relationship(back_populates="exposure_logs")


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    timestamp: datetime
    event_type: str  # failure / maintenance / inspection
    downtime_minutes: Optional[float] = 0.0
    description: Optional[str] = None

    asset: Asset = Relationship(back_populates="events")
    failure_details: list["EventFailureDetail"] = Relationship(back_populates="event")


class FailureMode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    category: Optional[str] = None

    event_details: list["EventFailureDetail"] = Relationship(back_populates="failure_mode")


class EventFailureDetail(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id")
    failure_mode_id: int = Field(foreign_key="failuremode.id")
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None
    part_replaced: Optional[str] = None

    event: Event = Relationship(back_populates="failure_details")
    failure_mode: FailureMode = Relationship(back_populates="event_details")


class Part(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    part_number: Optional[str] = None

    installs: list["PartInstall"] = Relationship(back_populates="part")


class PartInstall(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="asset.id")
    part_id: int = Field(foreign_key="part.id")
    install_time: datetime
    remove_time: Optional[datetime] = None

    asset: Asset = Relationship(back_populates="part_installs")
    part: Part = Relationship(back_populates="installs")
