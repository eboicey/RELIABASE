import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createExposure, deleteExposure, listAssets, listExposures, updateExposure } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { format } from "date-fns";
import { MetricTooltip } from "../components/MetricTooltip";

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
  const [filterAsset, setFilterAsset] = useState<number | "all">("all");
  const { data: exposures, isLoading, isError } = useQuery({
    queryKey: ["exposures", filterAsset],
    queryFn: () => listExposures({ limit: 500, asset_id: filterAsset === "all" ? undefined : filterAsset }),
  });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });

  const [editingId, setEditingId] = useState<number | null>(null);

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

  const editForm = useForm<ExposureForm>({
    resolver: zodResolver(exposureSchema),
    defaultValues: {
      asset_id: assets?.[0]?.id ?? 1,
      start_time: "",
      end_time: "",
      hours: undefined,
      cycles: undefined,
    },
  });

  const editingLog = useMemo(() => exposures?.find((l) => l.id === editingId), [exposures, editingId]);
  const assetMap = useMemo(() => new Map((assets ?? []).map((a) => [a.id, a.name])), [assets]);

  useEffect(() => {
    if (!editingLog) return;
    const toLocal = (iso: string) => iso.slice(0, 16);
    editForm.reset({
      asset_id: editingLog.asset_id,
      start_time: toLocal(editingLog.start_time),
      end_time: toLocal(editingLog.end_time),
      hours: editingLog.hours,
      cycles: editingLog.cycles,
    });
  }, [editingLog, editForm]);

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

  const updateMutation = useMutation({
    mutationFn: (values: ExposureForm) =>
      updateExposure(editingId!, {
        asset_id: values.asset_id,
        start_time: new Date(values.start_time).toISOString(),
        end_time: new Date(values.end_time).toISOString(),
        hours: values.hours,
        cycles: values.cycles,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["exposures"] });
      setEditingId(null);
    },
  });

  return (
    <div className="space-y-6">
      <Card title="Log exposure" description="Hours default to duration if omitted." actions={
          <MetricTooltip
            label="Exposure Logs"
            what="Exposure logs record the operating hours and cycles for each asset over specific time periods."
            why="Accurate exposure data is the denominator for every time-based reliability metric (MTBF, failure rate, availability). Without it, reliability analysis is impossible."
            basis="Reliability R(t) = e^(-λt) requires accurate operating time t. Exposure hours are to reliability what odometer readings are to automotive maintenance."
            interpret="Log exposure consistently for every operating period. Gaps in exposure data will inflate MTBF estimates and distort Weibull analysis results."
          />
        }>
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
        {isError && <Alert tone="danger">Could not load exposures.</Alert>}
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
                    <Td>
                      #{log.asset_id} — {assetMap.get(log.asset_id) ?? "Asset"}
                    </Td>
                    <Td>{format(new Date(log.start_time), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>{format(new Date(log.end_time), "yyyy-MM-dd HH:mm")}</Td>
                    <Td>{log.hours.toFixed(2)}</Td>
                    <Td>{log.cycles ?? 0}</Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-slate-200"
                        onClick={() => setEditingId(log.id)}
                      >
                        Edit
                      </Button>
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
        ) : !isLoading ? (
          <EmptyState title="No exposure logs" message="Log operating hours to power MTBF/availability." icon="⏳" />
        ) : null}
      </Card>

      {editingId && editingLog && (
        <Card
          title={`Edit exposure #${editingId}`}
          description="Adjust interval; overlap validation enforced by API."
          actions={<span className="text-xs text-slate-400">PATCH /exposures/{editingId}</span>}
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
            <Input label="Start" type="datetime-local" {...editForm.register("start_time")} />
            <Input label="End" type="datetime-local" {...editForm.register("end_time")} />
            <Input label="Hours" type="number" step="0.1" {...editForm.register("hours", { valueAsNumber: true })} />
            <Input label="Cycles" type="number" step="0.1" {...editForm.register("cycles", { valueAsNumber: true })} />
            <div className="self-end flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setEditingId(null)}>
                Cancel
              </Button>
            </div>
          </form>
          {updateMutation.isError && <p className="text-sm text-red-400 mt-2">Could not update exposure.</p>}
        </Card>
      )}
    </div>
  );
}
