import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures, listFailureModes, listParts, getHealth, seedDemo } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
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
