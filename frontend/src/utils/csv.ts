import type { Asset, EventItem, ExposureLog, FailureMode, Part } from "../api/types";

function downloadCSV(rows: string[][], filename: string) {
  const csv = rows.map((r) => r.map((cell) => JSON.stringify(cell ?? "")).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function exportAssets(items: Asset[]) {
  const header = ["id", "name", "type", "serial", "in_service_date", "notes"];
  const rows = items.map((a) => [a.id, a.name, a.type ?? "", a.serial ?? "", a.in_service_date ?? "", a.notes ?? ""]);
  downloadCSV([header, ...rows.map((r) => r.map(String))], "assets.csv");
}

export function exportEvents(items: EventItem[]) {
  const header = ["id", "asset_id", "timestamp", "event_type", "downtime_minutes", "description"];
  const rows = items.map((e) => [e.id, e.asset_id, e.timestamp, e.event_type, e.downtime_minutes ?? "", e.description ?? ""]);
  downloadCSV([header, ...rows.map((r) => r.map(String))], "events.csv");
}

export function exportExposures(items: ExposureLog[]) {
  const header = ["id", "asset_id", "start_time", "end_time", "hours", "cycles"];
  const rows = items.map((l) => [l.id, l.asset_id, l.start_time, l.end_time, l.hours, l.cycles]);
  downloadCSV([header, ...rows.map((r) => r.map(String))], "exposures.csv");
}

export function exportFailureModes(items: FailureMode[]) {
  const header = ["id", "name", "category"];
  const rows = items.map((f) => [f.id, f.name, f.category ?? ""]);
  downloadCSV([header, ...rows.map((r) => r.map(String))], "failure_modes.csv");
}

export function exportParts(items: Part[]) {
  const header = ["id", "name", "part_number"];
  const rows = items.map((p) => [p.id, p.name, p.part_number ?? ""]);
  downloadCSV([header, ...rows.map((r) => r.map(String))], "parts.csv");
}
