import { useQuery } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures } from "../api/endpoints";
import { Card } from "../components/Card";
import { Stat } from "../components/Stat";
import { Table, Th, Td } from "../components/Table";
import { format } from "date-fns";
import { Button } from "../components/Button";
import { useCallback } from "react";

export default function Dashboard() {
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });
  const { data: events } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 200 }) });
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 200 }) });
  const copyCommand = useCallback((cmd: string) => {
    void navigator.clipboard?.writeText(cmd);
  }, []);

  const totalHours = exposures?.reduce((sum, log) => sum + (log.hours ?? 0), 0) ?? 0;
  const failureCount = events?.filter((e) => e.event_type === "failure").length ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <Stat label="Assets" value={`${assets?.length ?? 0}`} hint="Total tracked" />
        <Stat label="Events" value={`${events?.length ?? 0}`} hint="All event types" />
        <Stat label="Failures" value={`${failureCount}`} hint="Event type = failure" />
        <Stat label="Exposure hours" value={`${totalHours.toFixed(1)}`} hint="Sum of exposure logs" />
      </div>

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
          <p className="text-sm text-slate-400">No events yet. Seed demo data via backend CLI.</p>
        )}
      </Card>

      <Card title="Next steps" description="Run backend then use the left nav to manage assets, exposures, events, parts, and failure modes.">
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-300">
          <li className="flex items-center gap-3">
            <span>Start backend:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">uvicorn reliabase.api.main:app --reload</code>
            <Button size="sm" variant="ghost" onClick={() => copyCommand("uvicorn reliabase.api.main:app --reload")}>Copy</Button>
          </li>
          <li className="flex items-center gap-3">
            <span>Seed demo:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.seed_demo</code>
            <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.seed_demo")}>Copy</Button>
          </li>
          <li className="flex items-center gap-3">
            <span>Generate report:</span>
            <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.make_report --asset-id 1 --output-dir examples</code>
            <Button size="sm" variant="ghost" onClick={() => copyCommand("python -m reliabase.make_report --asset-id 1 --output-dir examples")}>Copy</Button>
          </li>
          <li>Use UI to CRUD assets/exposures/events, track parts installs, and capture failure details.</li>
        </ol>
      </Card>
    </div>
  );
}
