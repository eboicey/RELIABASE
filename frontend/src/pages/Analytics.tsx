import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useCallback, Suspense, lazy } from "react";
import { listAssets, listEvents, listExposures, listFailureModes, listEventDetails } from "../api/endpoints";
import { Card } from "../components/Card";
import { Stat } from "../components/Stat";
import { Table, Th, Td } from "../components/Table";
import { Button } from "../components/Button";
import { format } from "date-fns";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";

const ParetoChart = lazy(() => import("../components/charts/ParetoChart"));
const Sparkline = lazy(() => import("../components/charts/Sparkline"));

export default function Analytics() {
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });
  const { data: events, isLoading: eventsLoading, isError: eventsError } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 500 }) });
  const { data: exposures, isLoading: exposuresLoading, isError: exposuresError } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 500 }) });
  const { data: failureModes } = useQuery({ queryKey: ["failure-modes"], queryFn: () => listFailureModes({ limit: 500 }) });
  const { data: eventDetails } = useQuery({ queryKey: ["event-details"], queryFn: () => listEventDetails({ limit: 500 }) });
  const [selectedAssetId, setSelectedAssetId] = useState<number | "all">("all");

  const filtered = useMemo(() => {
    const assetFilter = selectedAssetId;
    const eventsFiltered = assetFilter === "all" ? events ?? [] : (events ?? []).filter((e) => e.asset_id === assetFilter);
    const exposuresFiltered = assetFilter === "all" ? exposures ?? [] : (exposures ?? []).filter((l) => l.asset_id === assetFilter);
    return { eventsFiltered, exposuresFiltered };
  }, [events, exposures, selectedAssetId]);

  const { failureCount, mtbfHours, mttrHours, availability } = useMemo(() => {
    const failureEvents = filtered.eventsFiltered.filter((e) => e.event_type === "failure");
    const totalExposure = filtered.exposuresFiltered.reduce((sum, l) => sum + (l.hours ?? 0), 0);
    const totalDowntimeHrs = failureEvents.reduce((sum, e) => sum + ((e.downtime_minutes ?? 0) / 60), 0);
    const failCount = failureEvents.length;
    const mtbf = failCount > 0 ? totalExposure / failCount : totalExposure;
    const mttr = failCount > 0 ? totalDowntimeHrs / failCount : 0;
    const avail = mtbf + mttr > 0 ? mtbf / (mtbf + mttr) : 1;
    return { failureCount: failCount, mtbfHours: mtbf, mttrHours: mttr, availability: avail };
  }, [filtered]);

  const failureModePareto = useMemo(() => {
    if (!eventDetails || !failureModes) return [] as { name: string; count: number }[];
    const assetEvents = new Map((events ?? []).map((e) => [e.id, e]));
    const counts: Record<number, number> = {};
    eventDetails.forEach((detail) => {
      const evt = assetEvents.get(detail.event_id);
      if (!evt) return;
      if (selectedAssetId !== "all" && evt.asset_id !== selectedAssetId) return;
      counts[detail.failure_mode_id] = (counts[detail.failure_mode_id] ?? 0) + 1;
    });
    return failureModes
      .map((fm) => ({ name: fm.name, count: counts[fm.id!] ?? 0 }))
      .filter((row) => row.count > 0)
      .sort((a, b) => b.count - a.count);
  }, [eventDetails, failureModes, events, selectedAssetId]);

  const copyCommand = useCallback((cmd: string) => {
    void navigator.clipboard?.writeText(cmd);
  }, []);

  const mtbfTrend = useMemo(() => {
    const failures = filtered.eventsFiltered
      .filter((e) => e.event_type === "failure")
      .slice()
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    if (failures.length < 2) return { labels: [], values: [] };
    const values: number[] = [];
    const labels: string[] = [];
    for (let i = 1; i < failures.length; i++) {
      const prev = new Date(failures[i - 1].timestamp).getTime();
      const curr = new Date(failures[i].timestamp).getTime();
      const hours = (curr - prev) / (1000 * 60 * 60);
      values.push(Number(hours.toFixed(2)));
      labels.push(`#${i + 1}`);
    }
    return { labels, values };
  }, [filtered.eventsFiltered]);

  const paretoChart = useMemo(() => {
    if (failureModePareto.length === 0) return null;
    return {
      labels: failureModePareto.map((row) => row.name),
      values: failureModePareto.map((row) => row.count),
    };
  }, [failureModePareto]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-3 items-center">
        <div>
          <label className="text-sm text-slate-200">Asset filter</label>
          <select
            className="mt-1 w-56 rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
            value={selectedAssetId === "all" ? "all" : selectedAssetId}
            onChange={(e) => setSelectedAssetId(e.target.value === "all" ? "all" : Number(e.target.value))}
          >
            <option value="all">All assets</option>
            {(assets ?? []).map((asset) => (
              <option key={asset.id} value={asset.id}>
                #{asset.id} — {asset.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <Stat label="Failures" value={failureCount.toString()} hint="Events where type=failure" />
        <Stat label="Total exposure (h)" value={filtered.exposuresFiltered.reduce((s, l) => s + (l.hours ?? 0), 0).toFixed(1)} />
        <Stat label="MTBF (h)" value={mtbfHours.toFixed(2)} hint="Exposure hours / failures" />
        <Stat label="MTTR (h)" value={mttrHours.toFixed(2)} hint="Downtime per failure" />
      </div>

      <Card title="Availability" description="Computed from MTBF / (MTBF + MTTR)">
        <div className="text-4xl font-semibold text-white">{(availability * 100).toFixed(2)}%</div>
        <p className="text-sm text-slate-400 mt-1">
          Derived on the fly from exposure logs and failure events. For full statistical Weibull fits and PDF reporting, run the backend CLI.
        </p>
      </Card>

      <Card title="Failure timeline" description="Latest 20 failure events sorted by time">
        {(eventsLoading || exposuresLoading) && <Spinner />}
        {(eventsError || exposuresError) && <Alert tone="danger">Could not load data for analytics.</Alert>}
        {filtered.eventsFiltered && filtered.eventsFiltered.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>Timestamp</Th>
                <Th>Asset</Th>
                <Th>Downtime (min)</Th>
                <Th>Description</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.eventsFiltered
                .filter((e) => e.event_type === "failure")
                .slice()
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .slice(0, 20)
                .map((evt) => (
                  <tr key={evt.id} className="odd:bg-ink-900">
                    <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>#{evt.asset_id}</Td>
                    <Td>{evt.downtime_minutes ?? 0}</Td>
                    <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        ) : !(eventsLoading || exposuresLoading) ? (
          <p className="text-sm text-slate-400">No failure events yet.</p>
        ) : null}
      </Card>

      <Card title="Failure mode Pareto" description="Counts of failure modes in event details" actions={<span className="text-xs text-slate-400">GET /event-details</span>}>
        {eventDetails === undefined && <Spinner />}
        {failureModePareto.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2">
            <Table>
              <thead>
                <tr>
                  <Th>Failure mode</Th>
                  <Th>Count</Th>
                </tr>
              </thead>
              <tbody>
                {failureModePareto.map((row) => (
                  <tr key={row.name} className="odd:bg-ink-900">
                    <Td>{row.name}</Td>
                    <Td>{row.count}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Suspense fallback={<Spinner />}>
              {paretoChart && <ParetoChart labels={paretoChart.labels} values={paretoChart.values} />}
            </Suspense>
          </div>
        ) : eventDetails && eventDetails.length === 0 ? (
          <p className="text-sm text-slate-400">Add failure details to populate Pareto.</p>
        ) : null}
      </Card>

      <Card title="MTBF trend" description="Time between consecutive failures (hours)" actions={<span className="text-xs text-slate-400">Derived from events</span>}>
        {mtbfTrend.values.length > 0 ? (
          <Suspense fallback={<Spinner />}>
            <Sparkline labels={mtbfTrend.labels} values={mtbfTrend.values} />
          </Suspense>
        ) : (
          <p className="text-sm text-slate-400">Log at least two failure events to see trend.</p>
        )}
      </Card>

      <Card title="How to get Weibull & PDF" description="Backend already supports full reporting; run CLI until an API endpoint exists.">
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-300">
          <li className="flex items-center gap-3">
            <span>Seed demo data:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.seed_demo</code>
              <Button variant="ghost" className="px-2 py-1 text-xs" onClick={() => copyCommand("python -m reliabase.seed_demo")}>Copy</Button>
          </li>
          <li className="flex items-center gap-3">
            <span>Generate report:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.make_report --asset-id 1 --output-dir examples</code>
              <Button
                variant="ghost"
                className="px-2 py-1 text-xs"
                onClick={() => copyCommand("python -m reliabase.make_report --asset-id 1 --output-dir examples")}
              >
              Copy
            </Button>
          </li>
          <li>Open the PDF and PNGs from <code className="bg-slate-800 px-2 py-1 rounded">examples/</code></li>
        </ol>
      </Card>
    </div>
  );
}
