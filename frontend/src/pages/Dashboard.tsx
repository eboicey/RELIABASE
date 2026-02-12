import { useQuery } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures, getHealth, seedDemo, getFleetHealthSummary } from "../api/endpoints";
import { Card } from "../components/Card";
import { Stat } from "../components/Stat";
import { Table, Th, Td } from "../components/Table";
import { format } from "date-fns";
import { Button } from "../components/Button";
import { useCallback, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert } from "../components/Alert";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });
  const { data: events } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 200 }) });
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 200 }) });
  const { data: health, isLoading: healthLoading } = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const [seedSuccess, setSeedSuccess] = useState(false);

  // Fleet health summary
  const { data: fleetHealth } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: () => getFleetHealthSummary({ limit: 50 }),
  });
  
  const copyCommand = useCallback((cmd: string) => {
    void navigator.clipboard?.writeText(cmd);
  }, []);

  const seedMutation = useMutation({
    mutationFn: () => seedDemo({ reset: true }),
    onSuccess: () => {
      setSeedSuccess(true);
      ["assets", "events", "exposures", "failure-modes", "event-details", "parts", "health"].forEach((key) =>
        queryClient.invalidateQueries({ queryKey: [key] })
      );
      setTimeout(() => setSeedSuccess(false), 3000);
    },
  });

  const totalHours = exposures?.reduce((sum, log) => sum + (log.hours ?? 0), 0) ?? 0;
  const failureCount = events?.filter((e) => e.event_type === "failure").length ?? 0;
  const backendOnline = health?.status === "ok";

  return (
    <div className="space-y-6">
      {/* Quick Status */}
      <div className="flex items-center gap-3 text-sm">
        <span className={`h-2 w-2 rounded-full ${healthLoading ? "bg-amber-400 animate-pulse" : backendOnline ? "bg-emerald-400" : "bg-red-400"}`} />
        <span className="text-slate-300">
          Backend: {healthLoading ? "Checking..." : backendOnline ? "Online" : "Offline — start the backend server"}
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <Stat label="Assets" value={`${assets?.length ?? 0}`} hint="Total tracked" />
        <Stat label="Events" value={`${events?.length ?? 0}`} hint="All event types" />
        <Stat label="Failures" value={`${failureCount}`} hint="Event type = failure" />
        <Stat label="Exposure hours" value={`${totalHours.toFixed(1)}`} hint="Sum of exposure logs" />
      </div>

      {/* Fleet Health Heatmap */}
      {fleetHealth && fleetHealth.length > 0 && assets && assets.length > 0 && (
        <Card title="Fleet Health" description="Asset health scores at a glance — click Analytics for full detail">
          <div className="grid gap-2 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {fleetHealth.map((hi, idx) => {
              const asset = assets[idx];
              const name = asset?.name ?? `Asset ${idx + 1}`;
              return (
                <div
                  key={idx}
                  className={`rounded-lg p-3 text-center border ${
                    hi.grade === "A" ? "bg-emerald-900/20 border-emerald-500/30" :
                    hi.grade === "B" ? "bg-green-900/20 border-green-500/30" :
                    hi.grade === "C" ? "bg-amber-900/20 border-amber-500/30" :
                    hi.grade === "D" ? "bg-orange-900/20 border-orange-500/30" :
                    "bg-red-900/20 border-red-500/30"
                  }`}
                >
                  <div className="text-xs text-slate-400 truncate" title={name}>{name}</div>
                  <div className={`text-2xl font-bold mt-1 ${
                    hi.grade === "A" ? "text-emerald-400" :
                    hi.grade === "B" ? "text-green-400" :
                    hi.grade === "C" ? "text-amber-400" :
                    hi.grade === "D" ? "text-orange-400" : "text-red-400"
                  }`}>
                    {hi.score.toFixed(0)}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">Grade {hi.grade}</div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Recent Events */}
      <Card
        title="Recent events"
        description="Latest activity across assets."
        actions={<span className="text-xs text-slate-400">showing up to 10</span>}
      >
        {events && events.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>Timestamp</Th>
                <Th>Asset</Th>
                <Th>Type</Th>
                <Th>Downtime (min)</Th>
                <Th>Description</Th>
              </tr>
            </thead>
            <tbody>
              {events
                .slice()
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .slice(0, 10)
                .map((evt) => (
                  <tr key={evt.id} className="odd:bg-ink-900">
                    <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>#{evt.asset_id}</Td>
                    <Td className="capitalize">{evt.event_type}</Td>
                    <Td>{evt.downtime_minutes ?? 0}</Td>
                    <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        ) : (
          <div className="text-sm text-slate-400 space-y-3">
            <p>No events yet. Click below to seed demo data or add records manually via the sidebar.</p>
            <Button onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending || !backendOnline}>
              {seedMutation.isPending ? "Seeding..." : "Seed Demo Data"}
            </Button>
            {seedSuccess && <Alert tone="success">Demo data seeded successfully!</Alert>}
            {seedMutation.isError && <Alert tone="danger">Failed to seed. Is the backend running?</Alert>}
          </div>
        )}
      </Card>

      {/* Getting Started Guide */}
      <Card title="Getting Started" description="Follow these steps to run RELIABASE locally.">
        <div className="space-y-4">
          {/* Step 1 */}
          <div className="border-l-2 border-accent-500/40 pl-4 py-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 text-xs font-bold">1</span>
              <span className="font-medium text-slate-100">Start the Backend (Terminal 1)</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload</code>
              <Button size="sm" variant="ghost" onClick={() => copyCommand("uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload")}>Copy</Button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Run from project root. API available at http://localhost:8000</p>
          </div>

          {/* Step 2 */}
          <div className="border-l-2 border-accent-500/40 pl-4 py-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 text-xs font-bold">2</span>
              <span className="font-medium text-slate-100">Start the Frontend (Terminal 2)</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">cd frontend && npm run dev</code>
              <Button size="sm" variant="ghost" onClick={() => copyCommand("cd frontend && npm run dev")}>Copy</Button>
            </div>
            <p className="text-xs text-slate-400 mt-1">UI available at http://localhost:5173</p>
          </div>

          {/* Step 3 */}
          <div className="border-l-2 border-accent-500/40 pl-4 py-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent-500/20 text-accent-400 text-xs font-bold">3</span>
              <span className="font-medium text-slate-100">Seed Demo Data</span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <Button size="sm" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending || !backendOnline}>
                {seedMutation.isPending ? "Seeding..." : "Seed via UI"}
              </Button>
              <span className="text-slate-500">or</span>
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">python -m reliabase.seed_demo</code>
              <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.seed_demo")}>Copy</Button>
            </div>
            {seedSuccess && <Alert tone="success">Demo data seeded!</Alert>}
          </div>

          {/* Step 4 */}
          <div className="border-l-2 border-slate-700 pl-4 py-2">
            <div className="flex items-center gap-2 mb-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-slate-700 text-slate-300 text-xs font-bold">4</span>
              <span className="font-medium text-slate-100">Generate Reports (Optional)</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <code className="bg-slate-800 px-3 py-1.5 rounded text-slate-200">python -m reliabase.make_report --asset-id 1 --output-dir ./examples</code>
              <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.make_report --asset-id 1 --output-dir ./examples")}>Copy</Button>
            </div>
            <p className="text-xs text-slate-400 mt-1">Creates PDF + PNG charts in the examples folder</p>
          </div>
        </div>
      </Card>

      {/* Quick Links */}
      <Card title="What's Next?" description="Explore the application.">
        <div className="grid gap-3 md:grid-cols-3 text-sm">
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="font-medium text-slate-100 mb-1">📊 Analytics</div>
            <p className="text-slate-400">View MTBF, MTTR, availability metrics and failure mode Pareto charts.</p>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="font-medium text-slate-100 mb-1">🛠️ Operations</div>
            <p className="text-slate-400">Re-seed data, check API health, and export tables to CSV.</p>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="font-medium text-slate-100 mb-1">📚 API Docs</div>
            <p className="text-slate-400">
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
