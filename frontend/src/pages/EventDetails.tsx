import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { createEventDetail, deleteEventDetail, listEventDetails, listEvents, listFailureModes } from "../api/endpoints";

const schema = z.object({
  event_id: z.coerce.number(),
  failure_mode_id: z.coerce.number(),
  root_cause: z.string().optional(),
  corrective_action: z.string().optional(),
  part_replaced: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function EventDetails() {
  const queryClient = useQueryClient();
  const { data: events, isLoading: eventsLoading } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 400 }) });
  const { data: modes, isLoading: modesLoading } = useQuery({ queryKey: ["failure-modes"], queryFn: () => listFailureModes({ limit: 200 }) });
  const { data: details, isLoading: detailsLoading, isError: detailsError } = useQuery({ queryKey: ["event-details"], queryFn: () => listEventDetails({ limit: 400 }) });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      event_id: events?.[0]?.id ?? 0,
      failure_mode_id: modes?.[0]?.id ?? 0,
      root_cause: "",
      corrective_action: "",
      part_replaced: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: FormValues) => createEventDetail(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["event-details"] });
      form.reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEventDetail(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["event-details"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Attach failure detail" description="Tie events to failure modes and corrective actions." actions={<span className="text-xs text-slate-400">POST /event-details/</span>}>
        <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <div>
            <label className="text-sm text-slate-200">Event</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              {...form.register("event_id", { valueAsNumber: true })}
            >
              {(events ?? []).map((evt) => (
                <option key={evt.id} value={evt.id}>
                  #{evt.id} — {evt.event_type} on asset {evt.asset_id}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-200">Failure mode</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              {...form.register("failure_mode_id", { valueAsNumber: true })}
            >
              {(modes ?? []).map((mode) => (
                <option key={mode.id} value={mode.id}>
                  #{mode.id} — {mode.name}
                </option>
              ))}
            </select>
          </div>
          <Input label="Root cause" placeholder="Fatigue" {...form.register("root_cause")} />
          <Input label="Corrective action" placeholder="Replace seal" {...form.register("corrective_action")} />
          <Input label="Part replaced" placeholder="Seal" {...form.register("part_replaced")} />
          <div className="self-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Event failure details" description="Pareto inputs for analytics." actions={<span className="text-xs text-slate-400">GET /event-details/</span>}>
        {detailsLoading && <Spinner />}
        {detailsError && <Alert tone="danger">Could not load failure details.</Alert>}
        {details && details.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Event</Th>
                <Th>Failure Mode</Th>
                <Th>Root cause</Th>
                <Th>Corrective action</Th>
                <Th>Part replaced</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {details.map((row) => (
                <tr key={row.id} className="odd:bg-ink-900">
                  <Td>#{row.id}</Td>
                  <Td>#{row.event_id}</Td>
                  <Td>#{row.failure_mode_id}</Td>
                  <Td className="text-slate-300">{row.root_cause ?? "—"}</Td>
                  <Td className="text-slate-300">{row.corrective_action ?? "—"}</Td>
                  <Td className="text-slate-300">{row.part_replaced ?? "—"}</Td>
                  <Td className="text-right">
                    <Button
                      variant="ghost"
                      className="text-red-300"
                      onClick={() => deleteMutation.mutate(row.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : !detailsLoading ? (
          <EmptyState title="No failure details" message="Attach failure modes to events for analytics." icon="⚙" />
        ) : null}
      </Card>
    </div>
  );
}
