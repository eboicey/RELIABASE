import { useQuery } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures, listFailureModes, listParts, getHealth } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { exportAssets, exportEvents, exportExposures, exportFailureModes, exportParts } from "../utils/csv";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { useCallback } from "react";

export default function Operations() {
  const { data: health, isLoading: healthLoading, isError: healthError } = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });
  const { data: events } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 500 }) });
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 500 }) });
  const { data: modes } = useQuery({ queryKey: ["failure-modes"], queryFn: () => listFailureModes({ limit: 500 }) });
  const { data: parts } = useQuery({ queryKey: ["parts"], queryFn: () => listParts({ limit: 500 }) });
  const copyCommand = useCallback((cmd: string) => {
    void navigator.clipboard?.writeText(cmd);
  }, []);

  return (
    <div className="space-y-6">
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

      <Card title="Demo + report" description="Run backend CLIs until HTTP endpoints exist for these actions.">
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-300">
          <li className="flex items-center gap-3">
            <span>Seed demo:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.seed_demo</code>
            <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.seed_demo")}>Copy</Button>
          </li>
          <li className="flex items-center gap-3">
            <span>Generate reliability packet:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.make_report --asset-id 1 --output-dir examples</code>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => copyCommand("python -m reliabase.make_report --asset-id 1 --output-dir examples")}
            >
              Copy
            </Button>
          </li>
          <li>CSV import (backend): use reliabase.io.csv_io helpers or extend API to add upload endpoints.</li>
        </ol>
        <p className="text-xs text-slate-400 mt-3">
          If you want UI-based CSV import or server-side report generation, expose API endpoints and we will wire them here.
        </p>
      </Card>
    </div>
  );
}
