import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useEffect, useState } from "react";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createAsset, deleteAsset, listAssets, updateAsset } from "../api/endpoints";
import type { AssetCreate } from "../api/types";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";

const assetSchema = z.object({
  name: z.string().min(1, "Name is required"),
  type: z.string().optional(),
  serial: z.string().optional(),
  in_service_date: z.string().optional(),
  notes: z.string().optional(),
});

export default function Assets() {
  const queryClient = useQueryClient();
  const { data: assets, isLoading, isError } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });

  const [editingId, setEditingId] = useState<number | null>(null);

  const form = useForm<AssetCreate>({
    resolver: zodResolver(assetSchema),
    defaultValues: { name: "", type: "", serial: "", in_service_date: "", notes: "" },
  });

  const createMutation = useMutation({
    mutationFn: (payload: AssetCreate) => createAsset(payload),
    onSuccess: () => {
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["assets"] });
    },
  });

  const editForm = useForm<AssetCreate>({
    resolver: zodResolver(assetSchema),
    defaultValues: { name: "", type: "", serial: "", in_service_date: "", notes: "" },
  });

  useEffect(() => {
    if (!editingId || !assets) return;
    const selected = assets.find((a) => a.id === editingId);
    if (selected) {
      editForm.reset({
        name: selected.name,
        type: selected.type ?? "",
        serial: selected.serial ?? "",
        in_service_date: selected.in_service_date ?? "",
        notes: selected.notes ?? "",
      });
    }
  }, [editingId, assets, editForm]);

  const updateMutation = useMutation({
    mutationFn: (payload: AssetCreate) => updateAsset(editingId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      setEditingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteAsset(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assets"] }),
  });

  return (
    <div className="space-y-6">
      <Card title="Add asset" description="Basic metadata; link exposures and events later." actions={<span className="text-xs text-slate-400">POST /assets/</span>}>
        <form
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
          onSubmit={form.handleSubmit((data) => createMutation.mutate(data))}
        >
          <Input label="Name" placeholder="Compressor A" {...form.register("name")} error={form.formState.errors.name?.message} />
          <Input label="Type" placeholder="pump" {...form.register("type")} />
          <Input label="Serial" placeholder="SN-001" {...form.register("serial")} />
          <Input label="In service date" type="date" {...form.register("in_service_date")} />
          <Input label="Notes" placeholder="Critical duty" {...form.register("notes")} />
          <div className="self-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
        {createMutation.isError && <p className="text-sm text-red-400 mt-2">Failed to create asset.</p>}
      </Card>

      <Card title="Assets" description="Sorted by creation" actions={<span className="text-xs text-slate-400">GET /assets/</span>}>
        {isLoading && <Spinner />}
        {isError && <Alert tone="danger">Could not load assets.</Alert>}
        {assets && assets.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Name</Th>
                <Th>Type</Th>
                <Th>Serial</Th>
                <Th>In service</Th>
                <Th>Notes</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {assets
                .slice()
                .sort((a, b) => a.id - b.id)
                .map((asset) => (
                  <tr key={asset.id} className="odd:bg-ink-900">
                    <Td>#{asset.id}</Td>
                    <Td>{asset.name}</Td>
                    <Td className="text-slate-300">{asset.type ?? "—"}</Td>
                    <Td className="text-slate-300">{asset.serial ?? "—"}</Td>
                    <Td className="text-slate-300">{asset.in_service_date ?? "—"}</Td>
                    <Td className="text-slate-300">{asset.notes ?? ""}</Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-slate-200"
                        onClick={() => setEditingId(asset.id)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        className="text-red-300 hover:text-red-200"
                        onClick={() => deleteMutation.mutate(asset.id)}
                      >
                        Delete
                      </Button>
                    </Td>
                  </tr>
                ))}
            </tbody>
          </Table>
        ) : !isLoading ? (
          <EmptyState title="No assets" message="Create one or seed the demo dataset." icon="🛠" />
        ) : null}
      </Card>

      {editingId && (
        <Card
          title={`Edit asset #${editingId}`}
          description="Update metadata and notes."
            actions={<span className="text-xs text-slate-400">PATCH /assets/{editingId}</span>}
        >
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={editForm.handleSubmit((data) => updateMutation.mutate(data))}>
            <Input label="Name" {...editForm.register("name")} error={editForm.formState.errors.name?.message} />
            <Input label="Type" {...editForm.register("type")} />
            <Input label="Serial" {...editForm.register("serial")} />
            <Input label="In service date" type="date" {...editForm.register("in_service_date")} />
            <Input label="Notes" {...editForm.register("notes")} />
            <div className="self-end flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setEditingId(null)}>
                Cancel
              </Button>
            </div>
          </form>
          {updateMutation.isError && <p className="text-sm text-red-400 mt-2">Failed to update asset.</p>}
        </Card>
      )}
    </div>
  );
}
