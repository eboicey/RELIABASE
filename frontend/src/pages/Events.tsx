import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { createEvent, deleteEvent, listAssets, listEvents, updateEvent } from "../api/endpoints";
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
  const [filterAsset, setFilterAsset] = useState<number | "all">("all");
  const { data: events, isLoading, isError } = useQuery({
    queryKey: ["events", filterAsset],
    queryFn: () => listEvents({ limit: 400, asset_id: filterAsset === "all" ? undefined : filterAsset }),
  });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });

  const [editingId, setEditingId] = useState<number | null>(null);

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

  const editForm = useForm<EventForm>({
    resolver: zodResolver(eventSchema),
    defaultValues: {
      asset_id: assets?.[0]?.id ?? 1,
      timestamp: "",
      event_type: "failure",
      downtime_minutes: 0,
      description: "",
    },
  });

  const editingEvent = useMemo(() => events?.find((e) => e.id === editingId), [events, editingId]);
  const assetMap = useMemo(() => new Map((assets ?? []).map((a) => [a.id, a.name])), [assets]);

  useEffect(() => {
    if (!editingEvent) return;
    editForm.reset({
      asset_id: editingEvent.asset_id,
      timestamp: editingEvent.timestamp.slice(0, 16),
      event_type: editingEvent.event_type,
      downtime_minutes: editingEvent.downtime_minutes ?? 0,
      description: editingEvent.description ?? "",
    });
  }, [editingEvent, editForm]);

  const updateMutation = useMutation({
    mutationFn: (values: EventForm) =>
      updateEvent(editingId!, {
        asset_id: values.asset_id,
        event_type: values.event_type,
        timestamp: new Date(values.timestamp).toISOString(),
        downtime_minutes: values.downtime_minutes,
        description: values.description,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      setEditingId(null);
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
        <div className="flex gap-3 mb-3 items-center text-sm">
          <span className="text-slate-300">Filter by asset:</span>
          <select
            className="rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
            value={filterAsset}
            onChange={(e) => setFilterAsset(e.target.value === "all" ? "all" : Number(e.target.value))}
          >
            <option value="all">All assets</option>
            {(assets ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                #{a.id} — {a.name}
              </option>
            ))}
          </select>
        </div>
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
                    <Td>
                      #{evt.asset_id} — {assetMap.get(evt.asset_id) ?? "Asset"}
                    </Td>
                    <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                    <Td className="capitalize">{evt.event_type}</Td>
                    <Td>{evt.downtime_minutes ?? 0}</Td>
                    <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-slate-200"
                        onClick={() => setEditingId(evt.id)}
                      >
                        Edit
                      </Button>
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

      {editingId && editingEvent && (
        <Card
          title={`Edit event #${editingId}`}
          description="Update timestamp, type, downtime, and description."
          actions={<span className="text-xs text-slate-400">PATCH /events/{editingId}</span>}
        >
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={editForm.handleSubmit((values) => updateMutation.mutate(values))}>
            <div>
              <label className="text-sm text-slate-200">Asset</label>
              <select
                className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
                {...editForm.register("asset_id", { valueAsNumber: true })}
              >
                {(assets ?? []).map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    #{asset.id} — {asset.name}
                  </option>
                ))}
              </select>
            </div>
            <Input label="Timestamp" type="datetime-local" {...editForm.register("timestamp")} />
            <div>
              <label className="text-sm text-slate-200">Event type</label>
              <select className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm" {...editForm.register("event_type")}>
                {EVENT_TYPES.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <Input label="Downtime (minutes)" type="number" step="0.1" {...editForm.register("downtime_minutes", { valueAsNumber: true })} />
            <Input label="Description" {...editForm.register("description")} />
            <div className="self-end flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setEditingId(null)}>
                Cancel
              </Button>
            </div>
          </form>
          {updateMutation.isError && <p className="text-sm text-red-400 mt-2">Could not update event.</p>}
        </Card>
      )}
    </div>
  );
}
