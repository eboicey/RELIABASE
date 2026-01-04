import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { createFailureMode, deleteFailureMode, listFailureModes, updateFailureMode } from "../api/endpoints";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Table, Th, Td } from "../components/Table";
import { EmptyState } from "../components/EmptyState";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { useEffect, useState } from "react";

const schema = z.object({ name: z.string().min(1), category: z.string().optional() });

type FormValues = z.infer<typeof schema>;

export default function FailureModes() {
  const queryClient = useQueryClient();
  const { data: modes, isLoading, isError } = useQuery({ queryKey: ["failure-modes"], queryFn: () => listFailureModes({ limit: 200 }) });
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: "", category: "" } });
  const editForm = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: "", category: "" } });
  const [editingId, setEditingId] = useState<number | null>(null);

  const createMutation = useMutation({
    mutationFn: (values: FormValues) => createFailureMode(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["failure-modes"] });
      form.reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteFailureMode(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["failure-modes"] }),
  });

  const updateMutation = useMutation({
    mutationFn: (values: FormValues) => updateFailureMode(editingId!, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["failure-modes"] });
      setEditingId(null);
    },
  });

  useEffect(() => {
    if (!editingId || !modes) return;
    const m = modes.find((item) => item.id === editingId);
    if (m) editForm.reset({ name: m.name, category: m.category ?? "" });
  }, [editingId, modes, editForm]);

  return (
    <div className="space-y-6">
      <Card title="Add failure mode" description="Use consistent categories to enable Pareto charts." actions={<span className="text-xs text-slate-400">POST /failure-modes/</span>}>
        <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}>
          <Input label="Name" placeholder="Seal leak" {...form.register("name")} />
          <Input label="Category" placeholder="Mechanical" {...form.register("category")} />
          <div className="self-end">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Failure modes" description="Link to event details" actions={<span className="text-xs text-slate-400">GET /failure-modes/</span>}>
        {isLoading && <Spinner />}
        {isError && <Alert tone="danger">Could not load failure modes.</Alert>}
        {modes && modes.length > 0 ? (
          <Table>
            <thead>
              <tr>
                <Th>ID</Th>
                <Th>Name</Th>
                <Th>Category</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody>
              {modes.map((mode) => (
                <tr key={mode.id} className="odd:bg-ink-900">
                  <Td>#{mode.id}</Td>
                  <Td>{mode.name}</Td>
                  <Td className="text-slate-300">{mode.category ?? "—"}</Td>
                  <Td className="text-right">
                    <Button variant="ghost" onClick={() => setEditingId(mode.id)}>
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      className="text-red-300"
                      onClick={() => deleteMutation.mutate(mode.id)}
                    >
                      Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : !isLoading ? (
          <EmptyState title="No failure modes" message="Create modes then attach to events." icon="⚠️" />
        ) : null}
      </Card>

      {editingId && (
        <Card
          title={`Edit failure mode #${editingId}`}
          description="Rename or recategorize a failure mode."
          actions={<span className="text-xs text-slate-400">PATCH /failure-modes/{id}</span>}
        >
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={editForm.handleSubmit((v) => updateMutation.mutate(v))}>
            <Input label="Name" {...editForm.register("name")} />
            <Input label="Category" {...editForm.register("category")} />
            <div className="self-end flex gap-2">
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save"}
              </Button>
              <Button variant="ghost" type="button" onClick={() => setEditingId(null)}>
                Cancel
              </Button>
            </div>
          </form>
          {updateMutation.isError && <p className="text-sm text-red-400 mt-2">Could not update failure mode.</p>}
        </Card>
      )}
    </div>
  );
}
