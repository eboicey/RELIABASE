import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { listEvents, listExposures } from "../api/endpoints";
import { Card } from "../components/Card";
import { Stat } from "../components/Stat";
import { Table, Th, Td } from "../components/Table";
import { format } from "date-fns";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";

export default function Analytics() {
  const { data: events, isLoading: eventsLoading, isError: eventsError } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 500 }) });
  const { data: exposures, isLoading: exposuresLoading, isError: exposuresError } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 500 }) });

  const { failureCount, mtbfHours, mttrHours, availability } = useMemo(() => {
    const failureEvents = (events ?? []).filter((e) => e.event_type === "failure");
    const totalExposure = (exposures ?? []).reduce((sum, l) => sum + (l.hours ?? 0), 0);
    const totalDowntimeHrs = failureEvents.reduce((sum, e) => sum + ((e.downtime_minutes ?? 0) / 60), 0);
    const failCount = failureEvents.length;
    const mtbf = failCount > 0 ? totalExposure / failCount : totalExposure;
    const mttr = failCount > 0 ? totalDowntimeHrs / failCount : 0;
    const avail = mtbf + mttr > 0 ? mtbf / (mtbf + mttr) : 1;
    return { failureCount: failCount, mtbfHours: mtbf, mttrHours: mttr, availability: avail };
  }, [events, exposures]);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
        <Stat label="Failures" value={failureCount.toString()} hint="Events where type=failure" />
        <Stat label="Total exposure (h)" value={((exposures ?? []).reduce((s, l) => s + (l.hours ?? 0), 0)).toFixed(1)} />
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
        {events && events.length > 0 ? (
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
              {events
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

      <Card title="How to get Weibull & PDF" description="Backend already supports full reporting; run CLI until an API endpoint exists.">
        <ol className="list-decimal list-inside space-y-2 text-sm text-slate-300">
          <li>Seed demo data: <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.seed_demo</code></li>
          <li>Generate report: <code className="bg-slate-800 px-2 py-1 rounded">python -m reliabase.make_report --asset-id 1 --output-dir examples</code></li>
          <li>Open the PDF and PNGs from <code className="bg-slate-800 px-2 py-1 rounded">examples/</code></li>
        </ol>
      </Card>
    </div>
  );
}
