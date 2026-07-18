import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronDown, ChevronUp, History, RefreshCcw, Save, TestTube2 } from "lucide-react";
import { api } from "@/lib/api";
import {
  MASTER_CHILD_KEY,
  VARIANT_WORKFLOWS,
  childKeyForSubject,
  childKeyForVariant,
  findMaster,
  findSubject,
  masterToSingleText,
  parseChildKey,
  subjectToSingleText,
  variantPayloadField,
} from "@/lib/promptUtils";
import type {
  PromptLayer,
  PromptTemplate,
  PromptVariant,
  PromptVersion,
  StructuralLayerConfig,
  SubjectPrompt,
  WorkflowLayerConfig,
} from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
};

export function PromptEditor({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const [parentWorkflow, setParentWorkflow] = useState("CATALOG_IMAGE");
  const [childKey, setChildKey] = useState(MASTER_CHILD_KEY);
  const [editorText, setEditorText] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [loadedSnapshot, setLoadedSnapshot] = useState("");
  const [previewText, setPreviewText] = useState("");
  const [showLayers, setShowLayers] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  const [showStructural, setShowStructural] = useState(false);
  const [currentLayers, setCurrentLayers] = useState<PromptLayer[]>([]);
  const [structuralLayers, setStructuralLayers] = useState<StructuralLayerConfig[]>([]);
  const [newVariantLabel, setNewVariantLabel] = useState("");
  const [showAddVariant, setShowAddVariant] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["prompts", "editor-data"],
    queryFn: async () => {
      const [templates, subjects, variants] = await Promise.all([
        api.get<PromptTemplate[]>("/prompts/templates"),
        api.get<SubjectPrompt[]>("/prompts/subjects"),
        api.get<PromptVariant[]>("/prompts/variants"),
      ]);
      return {
        templates: templates.data,
        subjects: subjects.data,
        variants: variants.data,
      };
    },
  });

  const prompts = data?.templates ?? [];
  const subjects = data?.subjects ?? [];
  const variants = data?.variants ?? [];

  const workflowVariants = useMemo(
    () => variants.filter((v) => v.workflow === parentWorkflow),
    [variants, parentWorkflow]
  );

  const childOptions = useMemo(() => {
    const items: { key: string; label: string }[] = [{ key: MASTER_CHILD_KEY, label: "Master Prompt" }];
    for (const type of jewelryTypes) {
      items.push({ key: childKeyForSubject(type), label: type });
    }
    if (VARIANT_WORKFLOWS.includes(parentWorkflow as (typeof VARIANT_WORKFLOWS)[number])) {
      for (const v of workflowVariants) {
        items.push({ key: childKeyForVariant(v.variant_key), label: v.label });
      }
    }
    return items;
  }, [jewelryTypes, parentWorkflow, workflowVariants]);

  const parsed = parseChildKey(childKey);
  const activeMaster = findMaster(prompts, parentWorkflow);
  const activeSubject =
    parsed.type === "subject" ? findSubject(subjects, parentWorkflow, parsed.jewelryType) : undefined;
  const activeVariant =
    parsed.type === "variant"
      ? variants.find((v) => v.workflow === parentWorkflow && v.variant_key === parsed.variantKey)
      : undefined;

  const entityId =
    parsed.type === "master"
      ? activeMaster?.id
      : parsed.type === "subject"
        ? activeSubject?.id
        : activeVariant?.id;

  const { data: versions = [], refetch: refetchVersions } = useQuery({
    queryKey: ["prompts", "versions", parsed.type, entityId],
    enabled: showVersions && !!entityId && parsed.type !== "variant",
    queryFn: async () => {
      if (!entityId) return [];
      if (parsed.type === "master") {
        const res = await api.get<PromptVersion[]>(`/prompts/templates/${entityId}/versions`);
        return res.data;
      }
      if (parsed.type === "subject") {
        const res = await api.get<PromptVersion[]>(`/prompts/subjects/${entityId}/versions`);
        return res.data;
      }
      return [];
    },
  });

  const { data: layerConfig, refetch: refetchLayerConfig } = useQuery({
    queryKey: ["prompts", "layer-config", parentWorkflow],
    enabled: parsed.type === "master",
    queryFn: async () => {
      const res = await api.get<WorkflowLayerConfig>(`/prompts/workflows/${parentWorkflow}/layer-config`);
      return res.data;
    },
  });

  useEffect(() => {
    if (layerConfig?.structural_layers) {
      setStructuralLayers(layerConfig.structural_layers);
    }
  }, [layerConfig]);

  const resolveEditorContent = useCallback(
    (workflow: string, key: string) => {
      const p = parseChildKey(key);
      if (p.type === "master") {
        const master = findMaster(prompts, workflow);
        if (!master) return { text: "", active: true, layers: [] as PromptLayer[] };
        return {
          text: masterToSingleText(master),
          active: master.is_active,
          layers: master.layers ?? [],
        };
      }
      if (p.type === "subject") {
        const subject = findSubject(subjects, workflow, p.jewelryType);
        return {
          text: subject ? subjectToSingleText(subject) : "",
          active: subject?.is_active ?? true,
          layers: subject?.layers ?? [],
        };
      }
      const variant = variants.find((v) => v.workflow === workflow && v.variant_key === p.variantKey);
      return { text: variant?.prompt_text || "", active: variant?.is_active ?? true, layers: [] as PromptLayer[] };
    },
    [prompts, subjects, variants]
  );

  useEffect(() => {
    if (isLoading) return;
    const valid = childOptions.some((o) => o.key === childKey);
    if (!valid) {
      setChildKey(MASTER_CHILD_KEY);
      return;
    }
    const { text, active, layers } = resolveEditorContent(parentWorkflow, childKey);
    setEditorText(text);
    setIsActive(active);
    setLoadedSnapshot(text);
    setCurrentLayers(layers);
    setPreviewText("");
  }, [isLoading, parentWorkflow, childKey, childOptions, resolveEditorContent]);

  const isDirty = editorText !== loadedSnapshot;

  const selectionLabel = useMemo(() => {
    const wf = workflows.find((w) => w.id === parentWorkflow)?.label || parentWorkflow;
    const child = childOptions.find((o) => o.key === childKey)?.label || childKey;
    return `${wf} → ${child}`;
  }, [workflows, parentWorkflow, childOptions, childKey]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const p = parseChildKey(childKey);
      if (p.type === "master") {
        const existing = findMaster(prompts, parentWorkflow);
        await api.post("/prompts/templates", {
          name: existing?.name || `${workflows.find((w) => w.id === parentWorkflow)?.label || parentWorkflow} Master`,
          workflow: parentWorkflow,
          prompt_text: editorText,
          is_active: isActive,
        });
      } else if (p.type === "subject") {
        await api.post("/prompts/subjects", {
          workflow: parentWorkflow,
          jewelry_type: p.jewelryType,
          prompt_text: editorText,
          is_active: isActive,
        });
      } else {
        const variant = variants.find(
          (v) => v.workflow === parentWorkflow && v.variant_key === p.variantKey
        );
        if (!variant) throw new Error("Variant not found");
        await api.post("/prompts/variants", {
          workflow: parentWorkflow,
          variant_key: variant.variant_key,
          label: variant.label,
          prompt_text: editorText,
          is_active: isActive,
        });
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      setLoadedSnapshot(editorText);
      toast.success("Prompt saved");
    },
    onError: () => toast.error("Failed to save prompt"),
  });

  const saveStructuralMutation = useMutation({
    mutationFn: async () => {
      await api.put(`/prompts/workflows/${parentWorkflow}/layer-config`, {
        structural_layers: structuralLayers,
      });
    },
    onSuccess: async () => {
      await refetchLayerConfig();
      toast.success("Structural layer config saved");
    },
    onError: () => toast.error("Failed to save structural config"),
  });

  const activateVersionMutation = useMutation({
    mutationFn: async (versionId: string) => {
      if (!entityId) return;
      if (parsed.type === "master") {
        await api.post(`/prompts/templates/${entityId}/activate/${versionId}`);
      } else if (parsed.type === "subject") {
        await api.post(`/prompts/subjects/${entityId}/activate/${versionId}`);
      }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      await refetchVersions();
      toast.success("Version activated");
    },
    onError: () => toast.error("Failed to activate version"),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const p = parseChildKey(childKey);
      const jewelry_type = p.type === "subject" ? p.jewelryType : jewelryTypes[0] || "Ring";
      const payload: Record<string, string> = {
        workflow: parentWorkflow,
        jewelry_type,
      };
      if (p.type === "variant") {
        const variant = variants.find(
          (v) => v.workflow === parentWorkflow && v.variant_key === p.variantKey
        );
        if (variant) {
          Object.assign(payload, variantPayloadField(parentWorkflow, variant.label));
        }
      }
      const res = await api.post<{ prompt: string }>("/prompts/test", payload);
      return res.data.prompt;
    },
    onSuccess: (text) => {
      setPreviewText(text);
      toast.success("Preview composed");
    },
    onError: () => toast.error("Preview failed"),
  });

  const addVariantMutation = useMutation({
    mutationFn: async () => {
      const label = newVariantLabel.trim();
      if (!label) throw new Error("Variant label required");
      if (!VARIANT_WORKFLOWS.includes(parentWorkflow as (typeof VARIANT_WORKFLOWS)[number])) {
        throw new Error("This workflow does not support variants");
      }
      const variant_key = label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_|_$/g, "");
      if (!variant_key) throw new Error("Invalid variant key");
      await api.post("/prompts/variants", {
        workflow: parentWorkflow,
        variant_key,
        label,
        prompt_text: editorText || `${label} style guidance.`,
        is_active: true,
      });
      return variant_key;
    },
    onSuccess: async (variant_key) => {
      setNewVariantLabel("");
      setShowAddVariant(false);
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      setChildKey(childKeyForVariant(variant_key));
      toast.success("Variant added");
    },
    onError: (err: Error) => toast.error(err.message || "Failed to add variant"),
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Prompt Editor</h2>
          <p className="text-xs text-slate-500 mt-1">Edit raw prompt text. Layers are derived automatically on save.</p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          disabled={isLoading}
          className="inline-flex h-8 items-center gap-1 rounded-lg border border-slate-200 px-3 text-[10px] font-bold text-slate-600 hover:bg-slate-50"
        >
          <RefreshCcw className={`size-3 ${isLoading ? "animate-spin" : ""}`} />
          Reload
        </button>
      </div>

      <div className="p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Workflow
            </label>
            <select
              value={parentWorkflow}
              onChange={(e) => {
                setParentWorkflow(e.target.value);
                setChildKey(MASTER_CHILD_KEY);
              }}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-500"
            >
              {workflows
                .filter((w) => w.id !== "RATE_TOOLS" && w.id !== "BULK_GENERATION")
                .map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.label}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Prompt piece
            </label>
            <select
              value={childKey}
              onChange={(e) => setChildKey(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-500"
            >
              {childOptions.map((opt) => (
                <option key={opt.key} value={opt.key}>
                  {opt.label}
                </option>
              ))}
            </select>
            {VARIANT_WORKFLOWS.includes(
              parentWorkflow as (typeof VARIANT_WORKFLOWS)[number],
            ) && (
              <div className="mt-2">
                {!showAddVariant ? (
                  <button
                    type="button"
                    onClick={() => setShowAddVariant(true)}
                    className="text-[11px] font-semibold text-blue-600 hover:underline"
                  >
                    + Add variant
                  </button>
                ) : (
                  <div className="flex gap-2">
                    <input
                      value={newVariantLabel}
                      onChange={(e) => setNewVariantLabel(e.target.value)}
                      placeholder="Variant label (e.g. Emerald)"
                      className="h-9 flex-1 rounded-lg border border-slate-200 px-2 text-xs outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <button
                      type="button"
                      onClick={() => addVariantMutation.mutate()}
                      disabled={addVariantMutation.isPending}
                      className="rounded-lg bg-blue-600 px-3 text-[11px] font-bold text-white"
                    >
                      Add
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddVariant(false);
                        setNewVariantLabel("");
                      }}
                      className="rounded-lg border border-slate-200 px-2 text-[11px] font-semibold text-slate-600"
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-blue-100 bg-blue-50/40 px-3 py-2 text-[11px] font-medium text-blue-800">
          Editing: <span className="font-bold">{selectionLabel}</span>
          {isDirty && <span className="ml-2 text-amber-700">• unsaved</span>}
        </div>

        <textarea
          value={editorText}
          onChange={(e) => setEditorText(e.target.value)}
          disabled={isLoading}
          placeholder="Write the full prompt for this selection…"
          className="min-h-[280px] w-full rounded-xl border border-slate-200 bg-white p-4 text-sm leading-relaxed text-slate-800 outline-none focus:ring-2 focus:ring-blue-500 resize-y font-mono"
        />

        <div className="rounded-xl border border-slate-200 overflow-hidden">
          <button
            type="button"
            onClick={() => setShowLayers((v) => !v)}
            className="flex w-full items-center justify-between bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-700"
          >
            Derived Layers Preview (read-only)
            {showLayers ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </button>
          {showLayers && (
            <div className="max-h-48 overflow-y-auto p-4 space-y-2">
              {currentLayers.length === 0 ? (
                <p className="text-xs text-slate-500">No layers yet. Save to derive from raw text.</p>
              ) : (
                currentLayers.map((layer) => (
                  <div key={`${layer.key}-${layer.order}`} className="rounded-lg border border-slate-100 p-2 text-[11px]">
                    <div className="flex items-center gap-2 font-semibold text-slate-800">
                      <span className="text-slate-400">#{layer.order}</span>
                      <span>{layer.label}</span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] uppercase">{layer.type}</span>
                      {layer.is_system && (
                        <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[9px] uppercase text-amber-800">
                          system
                        </span>
                      )}
                      {layer.enabled === false && (
                        <span className="rounded bg-red-100 px-1.5 py-0.5 text-[9px] uppercase text-red-700">
                          disabled
                        </span>
                      )}
                    </div>
                    {layer.content && (
                      <p className="mt-1 text-slate-600 line-clamp-2">{layer.content}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {parsed.type === "master" && (
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowStructural((v) => !v)}
              className="flex w-full items-center justify-between bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-700"
            >
              Structural Insert Points
              {showStructural ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>
            {showStructural && (
              <div className="p-4 space-y-3">
                {structuralLayers.map((layer, idx) => (
                  <div key={layer.key} className="flex items-center gap-3 text-xs">
                    <label className="flex items-center gap-2 min-w-[180px]">
                      <input
                        type="checkbox"
                        checked={layer.enabled !== false}
                        onChange={(e) => {
                          const next = [...structuralLayers];
                          next[idx] = { ...next[idx], enabled: e.target.checked };
                          setStructuralLayers(next);
                        }}
                      />
                      <span className="font-semibold">{layer.label}</span>
                      <span className="text-slate-400">({layer.type})</span>
                    </label>
                    <input
                      type="number"
                      min={1}
                      value={idx + 1}
                      disabled
                      className="h-8 w-16 rounded border border-slate-200 px-2 text-xs"
                      title="Order is managed by position in config"
                    />
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => saveStructuralMutation.mutate()}
                  disabled={saveStructuralMutation.isPending}
                  className="inline-flex h-8 items-center rounded-lg bg-slate-800 px-3 text-[10px] font-bold text-white hover:bg-slate-900 disabled:opacity-60"
                >
                  Save structural config
                </button>
              </div>
            )}
          </div>
        )}

        {parsed.type !== "variant" && entityId && (
          <div className="rounded-xl border border-slate-200 overflow-hidden">
            <button
              type="button"
              onClick={() => setShowVersions((v) => !v)}
              className="flex w-full items-center justify-between bg-slate-50 px-4 py-2.5 text-xs font-bold text-slate-700"
            >
              <span className="inline-flex items-center gap-1.5">
                <History className="size-3.5" />
                Version History
              </span>
              {showVersions ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
            </button>
            {showVersions && (
              <div className="max-h-40 overflow-y-auto p-4 space-y-2">
                {versions.length === 0 ? (
                  <p className="text-xs text-slate-500">No versions found.</p>
                ) : (
                  versions.map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-xs"
                    >
                      <div>
                        <span className="font-bold">v{v.version}</span>
                        {v.is_active && (
                          <span className="ml-2 rounded bg-green-100 px-1.5 py-0.5 text-[9px] font-bold text-green-800">
                            active
                          </span>
                        )}
                        {v.created_at && (
                          <span className="ml-2 text-slate-400">{new Date(v.created_at).toLocaleString()}</span>
                        )}
                      </div>
                      {!v.is_active && (
                        <button
                          type="button"
                          onClick={() => activateVersionMutation.mutate(v.id)}
                          disabled={activateVersionMutation.isPending}
                          className="rounded border border-slate-200 px-2 py-1 text-[10px] font-bold hover:bg-slate-50"
                        >
                          Activate
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <label className="flex items-center gap-2 text-xs font-semibold text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="rounded border-slate-300"
            />
            Active
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => previewMutation.mutate()}
              disabled={previewMutation.isPending || isLoading}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-4 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <TestTube2 className="size-3.5" />
              {previewMutation.isPending ? "Previewing…" : "Preview"}
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || isLoading || !isDirty}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-blue-600 px-4 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              <Save className="size-3.5" />
              {saveMutation.isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </div>

        {previewText && (
          <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-4 text-[11px] font-mono text-slate-700">
            {previewText}
          </pre>
        )}
      </div>
    </div>
  );
}
