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


# ---------------------------------------------------------------------------
# Extended Analytics Schemas
# ---------------------------------------------------------------------------

class OEEOut(SQLModel):
    """OEE breakdown returned by manufacturing analytics."""
    availability: float
    performance: float
    quality: float
    oee: float


class PerformanceRateOut(SQLModel):
    actual_throughput: float
    design_throughput: float
    performance_rate: float
    total_cycles: float
    total_operating_hours: float


class DowntimeSplitOut(SQLModel):
    planned_downtime_hours: float
    unplanned_downtime_hours: float
    total_downtime_hours: float
    unplanned_ratio: float
    planned_count: int
    unplanned_count: int


class MTBMOut(SQLModel):
    mtbm_hours: float
    maintenance_events: int
    total_operating_hours: float


class ManufacturingKPIsOut(SQLModel):
    oee: OEEOut
    performance: PerformanceRateOut
    downtime_split: DowntimeSplitOut
    mtbm: MTBMOut


class FailureRateOut(SQLModel):
    average_rate: float
    instantaneous_rate: float
    total_failures: int
    total_hours: float


class BLifeOut(SQLModel):
    percentile: float
    life_hours: float


class ConditionalReliabilityOut(SQLModel):
    current_age: float
    mission_time: float
    conditional_reliability: float


class RepairEffectivenessOut(SQLModel):
    trend_ratio: float
    intervals_count: int
    improving: bool


class RPNEntryOut(SQLModel):
    failure_mode: str
    severity: int
    occurrence: int
    detection: int
    rpn: int


class RPNAnalysisOut(SQLModel):
    entries: list[RPNEntryOut] = []
    max_rpn: int = 0


class BadActorEntryOut(SQLModel):
    asset_id: int
    asset_name: str
    failure_count: int
    total_downtime_hours: float
    availability: float
    composite_score: float


class COUROut(SQLModel):
    total_cost: float
    lost_production_cost: float
    repair_cost: float
    unplanned_downtime_hours: float
    failure_count: int
    cost_per_failure: float


class PMOptimizationOut(SQLModel):
    weibull_shape: float
    failure_pattern: str
    recommended_pm_hours: float
    current_pm_hours: Optional[float] = None
    pm_ratio: Optional[float] = None
    assessment: str


class SparePartForecastOut(SQLModel):
    part_name: str
    expected_failures: float
    lower_bound: float
    upper_bound: float


class SpareDemandOut(SQLModel):
    horizon_hours: float
    forecasts: list[SparePartForecastOut] = []
    total_expected_failures: float = 0.0


class AssetHealthIndexOut(SQLModel):
    score: float
    grade: str
    components: dict = {}


class ExtendedAssetAnalytics(SQLModel):
    """Full unified analytics for one asset — reliability + manufacturing + business."""
    asset_id: int
    asset_name: str

    # Reliability core
    mtbf_hours: float = 0.0
    mttr_hours: float = 0.0
    availability: float = 0.0
    failure_count: int = 0
    total_exposure_hours: float = 0.0

    # Extended reliability
    failure_rate: Optional[FailureRateOut] = None
    b10_life: Optional[BLifeOut] = None
    mttf_hours: Optional[float] = None
    repair_effectiveness: Optional[RepairEffectivenessOut] = None
    rpn: Optional[RPNAnalysisOut] = None

    # Manufacturing
    manufacturing: Optional[ManufacturingKPIsOut] = None

    # Business
    cour: Optional[COUROut] = None
    pm_optimization: Optional[PMOptimizationOut] = None
    health_index: Optional[AssetHealthIndexOut] = None
