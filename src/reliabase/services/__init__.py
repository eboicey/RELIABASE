"""Service layer for RELIABASE - shared by Streamlit and FastAPI.

This module provides a clean abstraction over database operations,
making the codebase easily portable between Streamlit and API-based architectures.
"""
from .assets import AssetService
from .events import EventService
from .exposures import ExposureService
from .failure_modes import FailureModeService
from .event_details import EventDetailService
from .parts import PartService
from .demo import DemoService

__all__ = [
    "AssetService",
    "EventService",
    "ExposureService",
    "FailureModeService",
    "EventDetailService",
    "PartService",
    "DemoService",
]
