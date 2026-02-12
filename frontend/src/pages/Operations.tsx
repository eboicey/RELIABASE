import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures, listFailureModes, listParts, getHealth, seedDemo, getSpareDemandForecast, getBadActors } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Table, Th, Td } from "../components/Table";
import { exportAssets, exportEvents, exportExposures, exportFailureModes, exportParts } from "../utils/csv";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { useCallback, useState } from "react";
import type { SeedResponse } from "../api/types";

export default function Operations() {
  const queryClient = useQueryClient();
  const { data: health, isLoading: healthLoading, isError: healthError } = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });
  const { data: events } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 500 }) });
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 500 }) });
  const { data: modes } = useQuery({ queryKey: ["failure-modes"], queryFn: () => listFailureModes({ limit: 500 }) });
  const { data: parts } = useQuery({ queryKey: ["parts"], queryFn: () => listParts({ limit: 500 }) });
  const copyCommand = useCallback((cmd: string) => {
    void navigator.clipboard?.writeText(cmd);
  }, []);
  const [seedResult, setSeedResult] = useState<SeedResponse | null>(null);

  // Spare parts forecast
  const { data: spareDemand } = useQuery({
    queryKey: ["spare-demand"],
    queryFn: () => getSpareDemandForecast({ horizon_hours: 8760 }),
  });

  // Bad actors for ops overview
  const { data: badActors } = useQuery({
    queryKey: ["bad-actors-ops"],
    queryFn: () => getBadActors({ top_n: 5 }),
  });

  const seedMutation = useMutation({
    mutationFn: (reset: boolean) => seedDemo({ reset }),
    onSuccess: (data) => {
      setSeedResult(data);
      ["assets", "events", "exposures", "failure-modes", "event-details", "parts", "health"].forEach((key) =>
        queryClient.invalidateQueries({ queryKey: [key] })
      );
    },
  });

  return (
    <div className="space-y-6">
      <Card title="Demo dataset" description="Trigger backend seeding without touching the CLI">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Button onClick={() => seedMutation.mutate(true)} disabled={seedMutation.isPending}>
            {seedMutation.isPending ? "Seeding..." : "Seed demo data"}
          </Button>
          <Button variant="ghost" size="sm" onClick={() => seedMutation.mutate(false)} disabled={seedMutation.isPending}>
            Append without reset
          </Button>
          {seedMutation.isError && <Alert tone="danger">Seeding failed. Is the backend running?</Alert>}
        </div>
        {seedResult && (
          <div className="mt-3 text-sm text-slate-300 space-y-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              <span>Seeded {seedResult.created.assets} assets, {seedResult.created.events} events, {seedResult.created.exposures} exposures.</span>
            </div>
            <p className="text-xs text-slate-400">Totals now: {seedResult.totals.assets} assets, {seedResult.totals.events} events, {seedResult.totals.exposures} exposures.</p>
          </div>
        )}
      </Card>

      <Card title="API health" description="Pings /health on the backend">
        <div className="flex items-center gap-3 text-sm">
          <span className={`h-2 w-2 rounded-full ${healthLoading ? "bg-amber-400 animate-pulse" : health?.status === "ok" ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-slate-200">
            {healthLoading ? "Checking backend..." : healthError ? "Backend unreachable" : health?.status === "ok" ? "Backend reachable" : "Backend not reachable"}
          </span>
        </div>
      </Card>

      <Card title="CSV export" description="Download the current tables directly from API responses.">
        {(assets === undefined || events === undefined || exposures === undefined) && <Spinner />}
        <div className="flex flex-wrap gap-3">
          <Button onClick={() => assets && exportAssets(assets)} disabled={!assets}>Export assets</Button>
          <Button onClick={() => exposures && exportExposures(exposures)} disabled={!exposures}>Export exposures</Button>
          <Button onClick={() => events && exportEvents(events)} disabled={!events}>Export events</Button>
          <Button onClick={() => modes && exportFailureModes(modes)} disabled={!modes}>Export failure modes</Button>
          <Button onClick={() => parts && exportParts(parts)} disabled={!parts}>Export parts</Button>
        </div>
        {(events === null || exposures === null) && <Alert tone="danger">Could not load data to export.</Alert>}
      </Card>

      {/* Spare Parts Forecast */}
      {spareDemand && spareDemand.forecasts.length > 0 && (
        <Card title="Spare Parts Forecast" description={`Projected demand over ${(spareDemand.horizon_hours / 720).toFixed(0)} months (Poisson 90% CI)`}>
          <Table>
            <thead>
              <tr>
                <Th>Part</Th>
                <Th>Expected Failures</Th>
                <Th>Lower (5%)</Th>
                <Th>Upper (95%)</Th>
              </tr>
            </thead>
            <tbody>
              {spareDemand.forecasts.map((f) => (
                <tr key={f.part_name} className="odd:bg-ink-900">
                  <Td>{f.part_name}</Td>
                  <Td className="font-medium text-white">{f.expected_failures.toFixed(1)}</Td>
                  <Td>{f.lower_bound}</Td>
                  <Td>{f.upper_bound}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div className="mt-3 text-sm text-slate-400">
            Total expected replacements: <span className="text-white font-medium">{spareDemand.total_expected_failures.toFixed(1)}</span>
          </div>
        </Card>
      )}

      {/* Bad Actors Quick View */}
      {badActors && badActors.length > 0 && (
        <Card title="Worst Performers" description="Top 5 bad actors by composite unreliability score">
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-5">
            {badActors.map((ba, idx) => (
              <div key={ba.asset_id} className={`rounded-lg border p-3 text-center ${
                idx === 0 ? "bg-red-900/20 border-red-500/30" :
                idx === 1 ? "bg-orange-900/20 border-orange-500/30" :
                "bg-ink-900/50 border-slate-700"
              }`}>
                <div className="text-xs text-slate-400 truncate" title={ba.asset_name}>{ba.asset_name}</div>
                <div className={`text-xl font-bold mt-1 ${idx < 2 ? "text-red-400" : "text-amber-400"}`}>
                  {ba.failure_count}
                </div>
                <div className="text-xs text-slate-500">failures</div>
                <div className="text-xs text-slate-400 mt-1">{ba.total_downtime_hours.toFixed(1)}h DT</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="CLI Commands" description="Generate reports and manage data via terminal commands.">
        <div className="space-y-4 text-sm">
          <div className="border-l-2 border-slate-700 pl-4">
            <div className="font-medium text-slate-100 mb-2">Seed Demo Data (CLI alternative)</div>
            <div className="flex items-center gap-3">
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">python -m reliabase.seed_demo</code>
              <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.seed_demo")}>Copy</Button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Creates sample assets, events, and exposures. Use the button above for UI-based seeding.</p>
          </div>
          
          <div className="border-l-2 border-slate-700 pl-4">
            <div className="font-medium text-slate-100 mb-2">Generate Reliability Report</div>
            <div className="flex items-center gap-3">
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">python -m reliabase.make_report --asset-id 1 --output-dir ./examples</code>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => copyCommand("python -m reliabase.make_report --asset-id 1 --output-dir ./examples")}
              >
                Copy
              </Button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Creates PDF report + PNG charts (Weibull curves, Pareto, timeline) in the specified folder.</p>
          </div>

          <div className="border-l-2 border-slate-700 pl-4">
            <div className="font-medium text-slate-100 mb-2">API Documentation</div>
            <p className="text-slate-300">
              Interactive API docs available at{" "}
              <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="text-accent-400 hover:underline">
                http://localhost:8000/docs
              </a>
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
