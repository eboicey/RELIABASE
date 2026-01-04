import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createExposure, deleteExposure, listAssets, listExposures } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { format } from "date-fns";

const exposureSchema = z.object({
  asset_id: z.coerce.number(),
  start_time: z.string().min(1),
  end_time: z.string().min(1),
  hours: z.coerce.number().optional(),
  cycles: z.coerce.number().optional(),
});

type ExposureForm = z.infer<typeof exposureSchema>;

export default function Exposures() {
  const queryClient = useQueryClient();
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 500 }) });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });

  const form = useForm<ExposureForm>({
    resolver: zodResolver(exposureSchema),
    defaultValues: {
      asset_id: assets?.[0]?.id ?? 1,
      start_time: "",
      end_time: "",
      hours: undefined,
      cycles: undefined,
    },
  });

  const createMutation = useMutation({
    mutationFn: async (values: ExposureForm) => {
      const payload = {
        asset_id: values.asset_id,
        start_time: new Date(values.start_time).toISOString(),
        end_time: new Date(values.end_time).toISOString(),
        hours: values.hours,
        cycles: values.cycles,
      };
      return createExposure(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exposures"] });
      form.reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteExposure(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["exposures"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Log exposure" description="Hours default to duration if omitted." actions={<span className="text-xs text-slate-400">POST /exposures/</span>}>
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
          <Input label="Start" type="datetime-local" {...form.register("start_time")} />
          <Input label="End" type="datetime-local" {...form.register("end_time")} />
          <Input label="Hours (optional)" type="number" step="0.1" {...form.register("hours", { valueAsNumber: true })} />
          <Input label="Cycles (optional)" type="number" step="0.1" {...form.register("cycles", { valueAsNumber: true })} />
          <div className="self-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
        {createMutation.isError && <p className="text-sm text-red-400 mt-2">Could not create exposure.</p>}
      </Card>

      <Card title="Exposure logs" description="Validate overlaps and durations." actions={<span className="text-xs text-slate-400">GET /exposures/</span>}>
        {exposures && exposures.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Asset</Th>
                <Th>Start</Th>
                <Th>End</Th>
                <Th>Hours</Th>
                <Th>Cycles</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {exposures
                .slice()
                .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
                .map((log) => (
                  <tr key={log.id} className="odd:bg-ink-900">
                    <Td>#{log.id}</Td>
                    <Td>#{log.asset_id}</Td>
                    <Td>{format(new Date(log.start_time), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>{format(new Date(log.end_time), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>{log.hours.toFixed(2)}</Td>
                    <Td>{log.cycles ?? 0}</Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-red-300"
                        onClick={() => deleteMutation.mutate(log.id)}
                      >
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        ) : (
          <EmptyState title="No exposure logs" message="Log operating hours to power MTBF/availability." icon="⏳" />
        )}
      </Card>
    </div>
  );
}
