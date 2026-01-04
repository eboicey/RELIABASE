import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { createEvent, deleteEvent, listAssets, listEvents } from "../api/endpoints";
import { format } from "date-fns";

const eventSchema = z.object({
  asset_id: z.coerce.number(),
  timestamp: z.string().min(1),
  event_type: z.string().min(1),
  downtime_minutes: z.coerce.number().optional(),
  description: z.string().optional(),
});

type EventForm = z.infer<typeof eventSchema>;

const EVENT_TYPES = [
  { value: "failure", label: "Failure" },
  { value: "maintenance", label: "Maintenance" },
  { value: "inspection", label: "Inspection" },
];

export default function Events() {
  const queryClient = useQueryClient();
  const { data: events, isLoading, isError } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 400 }) });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });

  const form = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      asset_id: assets?.[0]?.id ?? 1,
      timestamp: "",
      event_type: "failure",
      downtime_minutes: 0,
      description: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: EventForm) =>
      createEvent({
        asset_id: values.asset_id,
        event_type: values.event_type,
        timestamp: new Date(values.timestamp).toISOString(),
        downtime_minutes: values.downtime_minutes ?? 0,
        description: values.description,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      form.reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEvent(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["events"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Log event" description="Normalize event_type to failure/maintenance/inspection" actions={<span className="text-xs text-slate-400">POST /events/</span>}>
        <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={form.handleSubmit((values) => createMutation.mutate(values))}>
          <div>
            <label className="text-sm text-slate-200">Asset</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              {...form.register("asset_id", { valueAsNumber: true })}
            >
              {(assets ?? []).map((asset) => (
                <option key={asset.id} value={asset.id}>
                  #{asset.id} — {asset.name}
                </option>
              ))}
            </select>
          </div>
          <Input label="Timestamp" type="datetime-local" {...form.register("timestamp")} />
          <div>
            <label className="text-sm text-slate-200">Event type</label>
            <select className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm" {...form.register("event_type")}>
              {EVENT_TYPES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <Input label="Downtime (minutes)" type="number" step="0.1" {...form.register("downtime_minutes", { valueAsNumber: true })} />
          <Input label="Description" placeholder="Seal replaced" {...form.register("description")} />
          <div className="self-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
        {createMutation.isError && <p className="text-sm text-red-400 mt-2">Could not create event.</p>}
      </Card>

      <Card title="Events" description="Filter, edit, and delete" actions={<span className="text-xs text-slate-400">GET /events/</span>}>
        {isLoading && <Spinner />}
        {isError && <Alert tone="danger">Could not load events.</Alert>}
        {events && events.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Asset</Th>
                <Th>Timestamp</Th>
                <Th>Type</Th>
                <Th>Downtime</Th>
                <Th>Description</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {events
                .slice()
                .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                .map((evt) => (
                  <tr key={evt.id} className="odd:bg-ink-900">
                    <Td>#{evt.id}</Td>
                    <Td>#{evt.asset_id}</Td>
                    <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                    <Td className="capitalize">{evt.event_type}</Td>
                    <Td>{evt.downtime_minutes ?? 0}</Td>
                    <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-red-300"
                        onClick={() => deleteMutation.mutate(evt.id)}
                      >
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        ) : !isLoading ? (
          <EmptyState title="No events" message="Log a failure/maintenance/inspection to see trend." icon="📅" />
        ) : null}
      </Card>
    </div>
  );
}
