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
