export interface Asset {
  id: number;
  name: string;
  type?: string | null;
  serial?: string | null;
  in_service_date?: string | null;
  notes?: string | null;
}

export interface AssetCreate {
  name: string;
  type?: string | null;
  serial?: string | null;
  in_service_date?: string | null;
  notes?: string | null;
}

export interface ExposureLog {
  id: number;
  asset_id: number;
  start_time: string;
  end_time: string;
  hours: number;
  cycles: number;
}

export interface ExposureCreate {
  asset_id: number;
  start_time: string;
  end_time: string;
  hours?: number;
  cycles?: number;
}

export interface EventItem {
  id: number;
  asset_id: number;
  timestamp: string;
  event_type: string;
  downtime_minutes?: number | null;
  description?: string | null;
}

export interface EventCreate {
  asset_id: number;
  timestamp: string;
  event_type: string;
  downtime_minutes?: number;
  description?: string;
}

export interface FailureMode {
  id: number;
  name: string;
  category?: string | null;
}

export interface FailureModeCreate {
  name: string;
  category?: string | null;
}

export interface EventFailureDetail {
  id: number;
  event_id: number;
  failure_mode_id: number;
  root_cause?: string | null;
  corrective_action?: string | null;
  part_replaced?: string | null;
}

export interface EventFailureDetailCreate {
  event_id: number;
  failure_mode_id: number;
  root_cause?: string;
  corrective_action?: string;
  part_replaced?: string;
}

export interface Part {
  id: number;
  name: string;
  part_number?: string | null;
}

export interface PartCreate {
  name: string;
  part_number?: string | null;
}

export interface PartInstall {
  id: number;
  asset_id: number;
  part_id: number;
  install_time: string;
  remove_time?: string | null;
}

export interface PartInstallCreate {
  asset_id: number;
  install_time: string;
  remove_time?: string | null;
}

export interface Health {
  status: string;
}

export interface SeedResponse {
  status: string;
  reset: boolean;
  created: {
    assets: number;
    exposures: number;
    events: number;
    failure_details: number;
    parts: number;
    installs: number;
  };
  totals: {
    assets: number;
    exposures: number;
    events: number;
    failure_details: number;
    parts: number;
    installs: number;
  };
}

// Analytics types
export interface WeibullParams {
  shape: number;
  scale: number;
  log_likelihood: number;
  shape_ci: [number, number];
  scale_ci: [number, number];
}

export interface ReliabilityCurveData {
  times: number[];
  reliability: number[];
  hazard: number[];
}

export interface KPIMetrics {
  mtbf_hours: number;
  mttr_hours: number;
  availability: number;
  failure_count: number;
  total_exposure_hours: number;
}

export interface FailureModeCount {
  name: string;
  count: number;
  category?: string | null;
}

export interface EventSummary {
  id: number;
  timestamp: string;
  event_type: string;
  downtime_minutes: number;
  description?: string | null;
}

export interface AssetAnalytics {
  asset_id: number;
  asset_name: string;
  kpis: KPIMetrics;
  weibull: WeibullParams | null;
  curves: ReliabilityCurveData | null;
  failure_modes: FailureModeCount[];
  recent_events: EventSummary[];
  intervals_hours: number[];
  censored_flags: boolean[];
}

// ---------------------------------------------------------------------------
// Extended analytics types (reliability + manufacturing + business)
// ---------------------------------------------------------------------------

export interface OEEOut {
  availability: number;
  performance: number;
  quality: number;
  oee: number;
}

export interface PerformanceRateOut {
  actual_throughput: number;
  design_throughput: number;
  performance_rate: number;
  total_cycles: number;
  total_operating_hours: number;
}

export interface DowntimeSplitOut {
  planned_downtime_hours: number;
  unplanned_downtime_hours: number;
  total_downtime_hours: number;
  unplanned_ratio: number;
  planned_count: number;
  unplanned_count: number;
}

export interface MTBMOut {
  mtbm_hours: number;
  maintenance_events: number;
  total_operating_hours: number;
}

export interface ManufacturingKPIsOut {
  oee: OEEOut;
  performance: PerformanceRateOut;
  downtime_split: DowntimeSplitOut;
  mtbm: MTBMOut;
}

export interface FailureRateOut {
  average_rate: number;
  instantaneous_rate: number;
  total_failures: number;
  total_hours: number;
}

export interface BLifeOut {
  percentile: number;
  life_hours: number;
}

export interface ConditionalReliabilityOut {
  current_age: number;
  mission_time: number;
  conditional_reliability: number;
}

export interface RepairEffectivenessOut {
  trend_ratio: number;
  intervals_count: number;
  improving: boolean;
}

export interface RPNEntryOut {
  failure_mode: string;
  severity: number;
  occurrence: number;
  detection: number;
  rpn: number;
}

export interface RPNAnalysisOut {
  entries: RPNEntryOut[];
  max_rpn: number;
}

export interface BadActorEntryOut {
  asset_id: number;
  asset_name: string;
  failure_count: number;
  total_downtime_hours: number;
  availability: number;
  composite_score: number;
}

export interface COUROut {
  total_cost: number;
  lost_production_cost: number;
  repair_cost: number;
  unplanned_downtime_hours: number;
  failure_count: number;
  cost_per_failure: number;
}

export interface PMOptimizationOut {
  weibull_shape: number;
  failure_pattern: string;
  recommended_pm_hours: number;
  current_pm_hours: number | null;
  pm_ratio: number | null;
  assessment: string;
}

export interface SparePartForecastOut {
  part_name: string;
  expected_failures: number;
  lower_bound: number;
  upper_bound: number;
}

export interface SpareDemandOut {
  horizon_hours: number;
  forecasts: SparePartForecastOut[];
  total_expected_failures: number;
}

export interface AssetHealthIndexOut {
  score: number;
  grade: string;
  components: Record<string, number>;
}

export interface ExtendedAssetAnalytics {
  asset_id: number;
  asset_name: string;

  // Core reliability
  mtbf_hours: number;
  mttr_hours: number;
  availability: number;
  failure_count: number;
  total_exposure_hours: number;

  // Extended reliability
  failure_rate: FailureRateOut | null;
  b10_life: BLifeOut | null;
  mttf_hours: number | null;
  repair_effectiveness: RepairEffectivenessOut | null;
  rpn: RPNAnalysisOut | null;

  // Manufacturing
  manufacturing: ManufacturingKPIsOut | null;

  // Business
  cour: COUROut | null;
  pm_optimization: PMOptimizationOut | null;
  health_index: AssetHealthIndexOut | null;
}
