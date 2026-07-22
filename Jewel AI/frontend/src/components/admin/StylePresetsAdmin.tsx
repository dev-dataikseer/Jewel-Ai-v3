import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import type { StylePreset } from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
};

export function StylePresetsAdmin({ workflows }: Props) {
  const queryClient = useQueryClient();
  const nameRef = useRef<HTMLInputElement>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [workflow, setWorkflow] = useState("");
  const [description, setDescription] = useState("");
  const [promptAddon, setPromptAddon] = useState("");

  const { data: presets = [], isLoading } = useQuery({
    queryKey: ["style-presets", "admin"],
    queryFn: async () => (await api.get<StylePreset[]>("/prompts/presets")).data,
  });

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setWorkflow("");
    setDescription("");
    setPromptAddon("");
  };

  const startEdit = (p: StylePreset) => {
    setEditingId(p.id);
    setName(p.name);
    setWorkflow(p.workflow || "");
    setDescription(p.description || "");
    setPromptAddon(p.prompt_addon || "");
    nameRef.current?.focus();
  };

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!name.trim() || !promptAddon.trim()) {
        throw new Error("Name and prompt addon are required");
      }
      if (editingId) {
        await api.patch(`/prompts/presets/${editingId}`, {
          name: name.trim(),
          workflow: workflow || null,
          description: description.trim() || null,
          prompt_addon: promptAddon.trim(),
        });
      } else {
        await api.post("/prompts/presets", {
          name: name.trim(),
          workflow: workflow || null,
          description: description.trim() || null,
          prompt_addon: promptAddon.trim(),
        });
      }
    },
    onSuccess: () => {
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["style-presets"] });
      toast.success(editingId ? "Style preset updated" : "Style preset created");
    },
    onError: (err: Error) => toast.error(err.message || "Failed to save preset"),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/prompts/presets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["style-presets"] });
      toast.success("Preset deleted");
    },
    onError: () => toast.error("Failed to delete preset"),
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
        <h2 className="text-sm font-semibold text-slate-800">Style presets</h2>
        <p className="mt-1 text-xs text-slate-500">
          Presets append Admin-authored style text in Studio. Optional workflow scope.
        </p>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-2">
        <div className="space-y-3">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {editingId ? "Edit preset" : "New preset"}
          </p>
          <input
            ref={nameRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Name"
            className="ui-input"
          />
          <select
            value={workflow}
            onChange={(e) => setWorkflow(e.target.value)}
            className="ui-input"
          >
            <option value="">All workflows</option>
            {workflows
              .filter((w) => w.id !== "BULK_GENERATION")
              .map((w) => (
                <option key={w.id} value={w.id}>
                  {w.label}
                </option>
              ))}
          </select>
          <input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description (optional)"
            className="ui-input"
          />
          <textarea
            value={promptAddon}
            onChange={(e) => setPromptAddon(e.target.value)}
            placeholder="Prompt addon text…"
            className="min-h-[120px] w-full rounded-xl border border-slate-200 p-3 text-sm outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="ui-btn-primary"
            >
              {editingId ? (
                <>
                  <Pencil className="size-3.5" />
                  Update preset
                </>
              ) : (
                <>
                  <Plus className="size-3.5" />
                  Add preset
                </>
              )}
            </button>
            {editingId ? (
              <button type="button" className="ui-btn-secondary" onClick={resetForm}>
                Cancel
              </button>
            ) : null}
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Active presets
          </p>
          {isLoading && <p className="text-xs text-slate-500">Loading…</p>}
          {!isLoading && presets.length === 0 && (
            <EmptyState
              compact
              title="No presets yet"
              description="Create a preset on the left to append style text in Studio."
              action={
                <button
                  type="button"
                  className="ui-btn-primary"
                  onClick={() => nameRef.current?.focus()}
                >
                  Create preset
                </button>
              }
            />
          )}
          <ul className="max-h-[360px] space-y-2 overflow-y-auto">
            {presets.map((p) => (
              <li
                key={p.id}
                className="flex items-start justify-between gap-3 rounded-xl border border-slate-100 p-3"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-800">{p.name}</p>
                  <p className="text-[11px] text-slate-500">
                    {p.workflow || "All workflows"}
                    {p.description ? ` · ${p.description}` : ""}
                  </p>
                  <p className="mt-1 line-clamp-2 text-[11px] text-slate-600">
                    {p.prompt_addon}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    type="button"
                    onClick={() => startEdit(p)}
                    className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-50"
                    aria-label={`Edit ${p.name}`}
                  >
                    <Pencil className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(p.id)}
                    className="rounded-lg p-1.5 text-rose-600 hover:bg-rose-50"
                    aria-label={`Delete ${p.name}`}
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
