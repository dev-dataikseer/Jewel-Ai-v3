import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Save, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "@/lib/api";
import { DynamicParamForm } from "@/components/studio/DynamicParamForm";
import type { ModelDefinition } from "@/types";

export function ModelSettings() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<ModelDefinition | null>(null);
  const [draftParams, setDraftParams] = useState<Record<string, unknown>>({});

  const { data: models = [], isLoading } = useQuery({
    queryKey: ["models", "admin"],
    queryFn: async () => (await api.get<ModelDefinition[]>("/models/admin")).data,
  });

  const patchMutation = useMutation({
    mutationFn: async ({
      endpoint_id,
      body,
    }: {
      endpoint_id: string;
      body: { is_active?: boolean; default_params?: Record<string, unknown> };
    }) => {
      await api.patch(`/models/${endpoint_id}`, body);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      toast.success("Model updated");
      setEditing(null);
    },
    onError: () => toast.error("Failed to update model"),
  });

  if (isLoading) return <p className="text-sm text-slate-500">Loading models…</p>;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Model Catalog</h2>
        <p className="text-xs text-slate-500 mt-1">Enable or disable fal.ai models and edit default parameters.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Endpoint</th>
              <th className="px-4 py-3">Cost</th>
              <th className="px-4 py-3">Active</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.endpoint_id} className="border-t border-slate-100 hover:bg-slate-50/50">
                <td className="px-4 py-3 font-semibold text-slate-800">{m.display_name}</td>
                <td className="px-4 py-3 text-slate-600">{m.category}</td>
                <td className="px-4 py-3 font-mono text-[10px] text-slate-500 max-w-[200px] truncate" title={m.endpoint_id}>
                  {m.endpoint_id}
                </td>
                <td className="px-4 py-3 text-slate-600">{m.cost_per_call != null ? `$${m.cost_per_call}` : "—"}</td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() =>
                      patchMutation.mutate({
                        endpoint_id: m.endpoint_id,
                        body: { is_active: !m.is_active },
                      })
                    }
                    className="inline-flex items-center gap-1 text-slate-600 hover:text-blue-600"
                  >
                    {m.is_active ? (
                      <ToggleRight className="size-5 text-emerald-600" />
                    ) : (
                      <ToggleLeft className="size-5 text-slate-400" />
                    )}
                    {m.is_active ? "On" : "Off"}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => {
                      setEditing(m);
                      setDraftParams({ ...m.default_params });
                    }}
                    className="text-blue-600 font-bold hover:underline"
                  >
                    Edit defaults
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div className="border-t border-slate-100 p-6 bg-slate-50/30">
          <h3 className="text-sm font-bold text-slate-800 mb-1">{editing.display_name}</h3>
          <p className="text-[10px] font-mono text-slate-500 mb-4">{editing.endpoint_id}</p>
          <DynamicParamForm
            schema={editing.input_schema}
            values={draftParams}
            defaults={editing.default_params}
            onChange={setDraftParams}
          />
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={() =>
                patchMutation.mutate({
                  endpoint_id: editing.endpoint_id,
                  body: { default_params: draftParams },
                })
              }
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-blue-600 px-4 text-xs font-bold text-white"
            >
              <Save className="size-3.5" />
              Save defaults
            </button>
            <button
              type="button"
              onClick={() => setEditing(null)}
              className="h-9 rounded-lg border border-slate-200 px-4 text-xs font-bold text-slate-600"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
