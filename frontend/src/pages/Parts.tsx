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
import {
  createPart,
  createPartInstall,
  deletePart,
  deletePartInstall,
  listAssets,
  listPartInstalls,
  listParts,
  updatePart,
} from "../api/endpoints";
import { useEffect, useState } from "react";
import { format } from "date-fns";

const partSchema = z.object({ name: z.string().min(1), part_number: z.string().optional() });
const installSchema = z.object({
  part_id: z.coerce.number(),
  asset_id: z.coerce.number(),
  install_time: z.string().min(1),
  remove_time: z.string().optional(),
});

type PartForm = z.infer<typeof partSchema>;
type InstallForm = z.infer<typeof installSchema>;

export default function Parts() {
  const queryClient = useQueryClient();
  const { data: parts, isLoading: partsLoading, isError: partsError } = useQuery({ queryKey: ["parts"], queryFn: () => listParts({ limit: 200 }) });
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });
  const [selectedPartId, setSelectedPartId] = useState<number | null>(null);
  const [editingPartId, setEditingPartId] = useState<number | null>(null);

  const installsQuery = useQuery({
    queryKey: ["part-installs", selectedPartId],
    queryFn: () => listPartInstalls(selectedPartId ?? 0),
    enabled: selectedPartId != null,
  });

  const partForm = useForm<PartForm>({ resolver: zodResolver(partSchema), defaultValues: { name: "", part_number: "" } });
  const editPartForm = useForm<PartForm>({ resolver: zodResolver(partSchema), defaultValues: { name: "", part_number: "" } });
  const installForm = useForm<InstallForm>({
    resolver: zodResolver(installSchema),
    defaultValues: {
      part_id: selectedPartId ?? 0,
      asset_id: assets?.[0]?.id ?? 1,
      install_time: "",
      remove_time: "",
    },
  });

  const createPartMutation = useMutation({
    mutationFn: (values: PartForm) => createPart(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      partForm.reset();
    },
  });

  const updatePartMutation = useMutation({
    mutationFn: (values: PartForm) => updatePart(editingPartId!, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["parts"] });
      setEditingPartId(null);
    },
  });

  const deletePartMutation = useMutation({
    mutationFn: (id: number) => deletePart(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["parts"] }),
  });

  const createInstallMutation = useMutation({
    mutationFn: async (values: InstallForm) =>
      createPartInstall(values.part_id, {
        asset_id: values.asset_id,
        install_time: new Date(values.install_time).toISOString(),
        remove_time: values.remove_time ? new Date(values.remove_time).toISOString() : undefined,
      }),
      onSuccess: (_data, variables) => {
        queryClient.invalidateQueries({ queryKey: ["part-installs", variables.part_id] });
        installForm.reset({
          part_id: variables.part_id,
          asset_id: variables.asset_id,
          install_time: "",
          remove_time: "",
        });
    },
  });

  const deleteInstallMutation = useMutation({
    mutationFn: (id: number) => deletePartInstall(id),
    onSuccess: () => {
      if (selectedPartId) {
        queryClient.invalidateQueries({ queryKey: ["part-installs", selectedPartId] });
      }
    },
  });

  useEffect(() => {
    if (!editingPartId || !parts) return;
    const part = parts.find((p) => p.id === editingPartId);
    if (part) editPartForm.reset({ name: part.name, part_number: part.part_number ?? "" });
  }, [editingPartId, parts, editPartForm]);

  return (
    <div className="space-y-6">
      <Card title="Parts" description="Create parts to track installs." actions={<span className="text-xs text-slate-400">POST /parts/</span>}>
        <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={partForm.handleSubmit((v) => createPartMutation.mutate(v))}>
          <Input label="Name" placeholder="Seal" {...partForm.register("name")} />
          <Input label="Part number" placeholder="P-123" {...partForm.register("part_number")} />
          <div className="self-end">
            <Button type="submit" disabled={createPartMutation.isPending}>
              {createPartMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>

        {partsLoading && <Spinner />}
        {partsError && <Alert tone="danger">Could not load parts.</Alert>}
        {parts && parts.length > 0 ? (
          <Table className="mt-4">
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Name</Th>
                <Th>Number</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {parts.map((part) => (
                <tr key={part.id} className="odd:bg-ink-900">
                  <Td>#{part.id}</Td>
                  <Td>{part.name}</Td>
                  <Td className="text-slate-300">{part.part_number ?? "—"}</Td>
                  <Td className="text-right space-x-2">
                    <Button variant="ghost" onClick={() => setEditingPartId(part.id)}>
                      Edit
                    </Button>
                    <Button variant="ghost" onClick={() => setSelectedPartId(part.id)}>
                      Installs
                    </Button>
                    <Button
                      variant="ghost"
                      className="text-red-300"
                      onClick={() => deletePartMutation.mutate(part.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : !partsLoading ? (
          <EmptyState title="No parts" message="Create parts to track install/remove windows." icon="📦" />
        ) : null}
      </Card>

      {editingPartId && (
        <Card
          title={`Edit part #${editingPartId}`}
          description="Update part name or number."
          actions={<span className="text-xs text-slate-400">PATCH /parts/{editingPartId}</span>}
        >
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={editPartForm.handleSubmit((v) => updatePartMutation.mutate(v))}>
            <Input label="Name" {...editPartForm.register("name")} />
            <Input label="Part number" {...editPartForm.register("part_number")} />
            <div className="self-end flex gap-2">
              <Button type="submit" disabled={updatePartMutation.isPending}>
                {updatePartMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setEditingPartId(null)}>
                Cancel
              </Button>
            </div>
          </form>
          {updatePartMutation.isError && <p className="text-sm text-red-400 mt-2">Could not update part.</p>}
        </Card>
      )}

      <Card
        title="Part installs"
        description={selectedPartId ? `For part #${selectedPartId}` : "Select a part above to view installs."}
        actions={<span className="text-xs text-slate-400">POST /parts/{"{id}"}/installs</span>}
      >
        <form className="grid grid-cols-1 md:grid-cols-4 gap-4" onSubmit={installForm.handleSubmit((v) => createInstallMutation.mutate(v))}>
          <div>
            <label className="text-sm text-slate-200">Part</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              {...installForm.register("part_id", { valueAsNumber: true })}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedPartId(id);
                installForm.setValue("part_id", id);
              }}
              value={installForm.watch("part_id") || selectedPartId || ""}
            >
              <option value="">Select part</option>
              {(parts ?? []).map((part) => (
                <option key={part.id} value={part.id}>
                  #{part.id} — {part.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-200">Asset</label>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              {...installForm.register("asset_id", { valueAsNumber: true })}
            >
              {(assets ?? []).map((asset) => (
                <option key={asset.id} value={asset.id}>
                  #{asset.id} — {asset.name}
                </option>
              ))}
            </select>
          </div>
          <Input label="Install time" type="datetime-local" {...installForm.register("install_time")} />
          <Input label="Remove time" type="datetime-local" {...installForm.register("remove_time")} />
          <div className="self-end">
            <Button type="submit" disabled={createInstallMutation.isPending}>
              {createInstallMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
        {createInstallMutation.isError && <p className="text-sm text-red-400 mt-2">Could not create install.</p>}

        {installsQuery.isLoading && <Spinner />}
        {installsQuery.isError && <Alert tone="danger">Could not load installs.</Alert>}
        {selectedPartId && installsQuery.data && installsQuery.data.length > 0 ? (
          <Table className="mt-4">
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Asset</Th>
                <Th>Install</Th>
                <Th>Remove</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {installsQuery.data.map((row) => (
                <tr key={row.id} className="odd:bg-ink-900">
                  <Td>#{row.id}</Td>
                  <Td>#{row.asset_id}</Td>
                  <Td>{format(new Date(row.install_time), "yyyy-MM-dd HH:mm")}</Td>
                  <Td>{row.remove_time ? format(new Date(row.remove_time), "yyyy-MM-dd HH:mm") : "—"}</Td>
                  <Td className="text-right">
                    <Button
                      variant="ghost"
                      className="text-red-300"
                      onClick={() => deleteInstallMutation.mutate(row.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : !installsQuery.isLoading ? (
          <EmptyState
            title="No installs"
            message={selectedPartId ? "Log install/remove cycles for this part." : "Pick a part to view installs."}
            icon="🛠"
          />
        ) : null}
      </Card>
    </div>
  );
}
