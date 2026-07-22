import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, Eye, History, Save } from "lucide-react";
import { FacetMark } from "@/components/ui/FacetMark";
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
} from "@/lib/promptUtils";
import {
  downloadTextFile,
  sampleBodyFor,
  sampleFilename,
} from "@/lib/promptSamples";
import type { PromptTemplate, PromptVariant, PromptVersion, SubjectPrompt } from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
};

type ValidateResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
  char_count: number;
  word_count: number;
};

type AssemblePreview = {
  final_prompt?: string;
  prompt?: string;
  negative_prompt?: string | null;
  debug?: unknown;
};

function simpleDiff(a: string, b: string): { left: string; right: string; changed: boolean }[] {
  const la = a.split("\n");
  const lb = b.split("\n");
  const max = Math.max(la.length, lb.length);
  const rows: { left: string; right: string; changed: boolean }[] = [];
  for (let i = 0; i < max; i++) {
    const left = la[i] ?? "";
    const right = lb[i] ?? "";
    rows.push({ left, right, changed: left !== right });
  }
  return rows;
}

export function PromptEditor({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const [parentWorkflow, setParentWorkflow] = useState("CATALOG_IMAGE");
  const [childKey, setChildKey] = useState(MASTER_CHILD_KEY);
  const [editorText, setEditorText] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [loadedSnapshot, setLoadedSnapshot] = useState("");
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [preview, setPreview] = useState<AssemblePreview | null>(null);
  const [previewJewelry, setPreviewJewelry] = useState("Ring");
  const [previewAddon, setPreviewAddon] = useState("");
  const [showVersions, setShowVersions] = useState(false);
  const [diffAgainst, setDiffAgainst] = useState<PromptVersion | null>(null);

  const { data, isLoading } = useQuery({
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

  const visibleWorkflows = useMemo(
    () =>
      workflows.filter(
        (w) =>
          w.id !== "BULK_GENERATION" &&
          w.id !== "JEWELRY_ON_MODEL" &&
          w.id !== "CUSTOMER_TRY_ON" &&
          w.id !== "REFERENCE_STYLE_MATCH",
      ),
    [workflows],
  );

  const workflowVariants = useMemo(
    () => variants.filter((v) => v.workflow === parentWorkflow),
    [variants, parentWorkflow],
  );

  const childOptions = useMemo(() => {
    const items: { key: string; label: string }[] = [
      { key: MASTER_CHILD_KEY, label: "Master prompt" },
    ];
    for (const type of jewelryTypes) {
      items.push({ key: childKeyForSubject(type), label: type });
    }
    if (VARIANT_WORKFLOWS.includes(parentWorkflow as (typeof VARIANT_WORKFLOWS)[number])) {
      for (const v of workflowVariants) {
        items.push({ key: childKeyForVariant(v.variant_key), label: `Variant · ${v.label}` });
      }
    }
    return items;
  }, [jewelryTypes, parentWorkflow, workflowVariants]);

  const parsed = parseChildKey(childKey);

  const entityId = useMemo(() => {
    if (parsed.type === "master") return findMaster(prompts, parentWorkflow)?.id ?? null;
    if (parsed.type === "subject")
      return findSubject(subjects, parentWorkflow, parsed.jewelryType)?.id ?? null;
    return (
      variants.find((v) => v.workflow === parentWorkflow && v.variant_key === parsed.variantKey)
        ?.id ?? null
    );
  }, [parsed, prompts, subjects, variants, parentWorkflow]);

  const versionsPath = useMemo(() => {
    if (!entityId) return null;
    if (parsed.type === "master") return `/prompts/templates/${entityId}/versions`;
    if (parsed.type === "subject") return `/prompts/subjects/${entityId}/versions`;
    return `/prompts/variants/${entityId}/versions`;
  }, [entityId, parsed.type]);

  const activatePath = useCallback(
    (versionId: string) => {
      if (!entityId) return null;
      if (parsed.type === "master") return `/prompts/templates/${entityId}/activate/${versionId}`;
      if (parsed.type === "subject") return `/prompts/subjects/${entityId}/activate/${versionId}`;
      return `/prompts/variants/${entityId}/activate/${versionId}`;
    },
    [entityId, parsed.type],
  );

  const { data: versions = [], refetch: refetchVersions } = useQuery({
    queryKey: ["prompts", "versions", versionsPath],
    queryFn: async () => {
      if (!versionsPath) return [];
      return (await api.get<PromptVersion[]>(versionsPath)).data;
    },
    enabled: Boolean(versionsPath) && showVersions,
  });

  const resolveEditorContent = useCallback(
    (workflow: string, key: string) => {
      const p = parseChildKey(key);
      if (p.type === "master") {
        const master = findMaster(prompts, workflow);
        if (!master) return { text: "", active: true };
        return {
          text: masterToSingleText(master),
          active: master.is_active,
        };
      }
      if (p.type === "subject") {
        const subject = findSubject(subjects, workflow, p.jewelryType);
        return {
          text: subject ? subjectToSingleText(subject) : "",
          active: subject?.is_active ?? true,
        };
      }
      const variant = variants.find(
        (v) => v.workflow === workflow && v.variant_key === p.variantKey,
      );
      return {
        text: variant?.prompt_text || "",
        active: variant?.is_active ?? true,
      };
    },
    [prompts, subjects, variants],
  );

  useEffect(() => {
    if (isLoading) return;
    const valid = childOptions.some((o) => o.key === childKey);
    if (!valid) {
      setChildKey(MASTER_CHILD_KEY);
      return;
    }
    const { text, active } = resolveEditorContent(parentWorkflow, childKey);
    setEditorText(text);
    setIsActive(active);
    setLoadedSnapshot(text);
    setValidation(null);
    setPreview(null);
    setDiffAgainst(null);
  }, [isLoading, parentWorkflow, childKey, childOptions, resolveEditorContent]);

  const isDirty = editorText !== loadedSnapshot;

  const scope =
    parsed.type === "master" ? "master" : parsed.type === "subject" ? "subject" : "variant";

  const runValidate = async (): Promise<ValidateResult> => {
    const res = await api.post<ValidateResult>("/prompts/validate", {
      prompt_text: editorText,
      scope,
      workflow: parentWorkflow,
    });
    setValidation(res.data);
    return res.data;
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const result = await runValidate();
      if (!result.ok) {
        throw new Error(result.errors.join("; ") || "Validation failed");
      }
      if (parsed.type === "master") {
        const existing = findMaster(prompts, parentWorkflow);
        await api.post("/prompts/templates", {
          name:
            existing?.name ||
            `${workflows.find((w) => w.id === parentWorkflow)?.label || parentWorkflow} Master`,
          workflow: parentWorkflow,
          prompt_text: editorText,
          is_active: isActive,
        });
      } else if (parsed.type === "subject") {
        await api.post("/prompts/subjects", {
          workflow: parentWorkflow,
          jewelry_type: parsed.jewelryType,
          prompt_text: editorText,
          is_active: isActive,
        });
      } else {
        const variant = variants.find(
          (v) => v.workflow === parentWorkflow && v.variant_key === parsed.variantKey,
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
      if (showVersions) void refetchVersions();
    },
    onError: (err: Error & { friendlyMessage?: string }) =>
      toast.error(err.friendlyMessage || err.message || "Failed to save prompt"),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const jewelry =
        parsed.type === "subject" ? parsed.jewelryType : previewJewelry || "Ring";
      const params = new URLSearchParams({
        jewelry_type: jewelry,
      });
      if (previewAddon.trim()) params.set("prompt_text", previewAddon.trim());
      const res = await api.get<AssemblePreview>(
        `/pipelines/${parentWorkflow}/assemble?${params.toString()}`,
      );
      return res.data;
    },
    onSuccess: (data) => {
      setPreview(data);
      toast.message("Compose preview ready");
    },
    onError: (err: Error) => toast.error(err.message || "Preview failed"),
  });

  const activateMutation = useMutation({
    mutationFn: async (versionId: string) => {
      const path = activatePath(versionId);
      if (!path) throw new Error("No entity to activate");
      await api.post(path);
    },
    onSuccess: async () => {
      toast.success("Version activated");
      await queryClient.invalidateQueries({ queryKey: ["prompts"] });
      void refetchVersions();
    },
    onError: (err: Error) => toast.error(err.message || "Activate failed"),
  });

  const onDownloadSample = () => {
    const { kind, text } = sampleBodyFor(parentWorkflow, parsed.type);
    downloadTextFile(sampleFilename(kind), text);
    toast.message("Sample downloaded — keep {{placeholders}} when you paste");
  };

  const targetHint =
    parsed.type === "master"
      ? "Full workflow brief. Keep section labels and {{placeholders}}."
      : parsed.type === "subject"
        ? "Short jewelry-type grounding only (physics / contact / shadow)."
        : "Variant text for this workflow option.";

  const diffRows = diffAgainst
    ? simpleDiff(diffAgainst.prompt_text || "", editorText)
    : [];

  return (
    <div className="ui-card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--jewel-hairline)] bg-[var(--jewel-surface-muted)] px-5 py-4">
        <div className="min-w-0">
          <h2 className="ui-card-title">Workflow prompts</h2>
          <p className="mt-0.5 text-[12px] text-jewel-ink-muted">
            Download a fill-in template, copy the PASTE BLOCK, replace [BRACKETS], keep{" "}
            {"{{placeholders}}"}, then Save. Validation runs before save.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onDownloadSample}
            className="ui-btn-secondary h-9 shrink-0 text-[12px]"
          >
            <Download className="size-3.5" />
            Download sample
          </button>
          <button
            type="button"
            onClick={() => {
              setShowVersions((v) => !v);
            }}
            className="ui-btn-secondary h-9 shrink-0 text-[12px]"
            disabled={!entityId}
          >
            <History className="size-3.5" />
            Versions
          </button>
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="ui-label" htmlFor="prompt-workflow">
              Workflow
            </label>
            <select
              id="prompt-workflow"
              value={parentWorkflow}
              onChange={(e) => {
                setParentWorkflow(e.target.value);
                setChildKey(MASTER_CHILD_KEY);
              }}
              className="ui-input"
            >
              {visibleWorkflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="ui-label" htmlFor="prompt-target">
              Prompt
            </label>
            <select
              id="prompt-target"
              value={childKey}
              onChange={(e) => setChildKey(e.target.value)}
              className="ui-input"
            >
              <optgroup label="Workflow">
                {childOptions
                  .filter((o) => o.key === MASTER_CHILD_KEY)
                  .map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
              </optgroup>
              <optgroup label="Jewelry type">
                {childOptions
                  .filter((o) => o.key.startsWith("subject:"))
                  .map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
              </optgroup>
              {childOptions.some((o) => o.key.startsWith("variant:")) ? (
                <optgroup label="Variants">
                  {childOptions
                    .filter((o) => o.key.startsWith("variant:"))
                    .map((o) => (
                      <option key={o.key} value={o.key}>
                        {o.label}
                      </option>
                    ))}
                </optgroup>
              ) : null}
            </select>
          </div>
        </div>

        <p className="text-[11px] text-jewel-ink-muted leading-relaxed">{targetHint}</p>

        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <label className="ui-label mb-0" htmlFor="prompt-body">
                Prompt text
              </label>
              {isDirty ? (
                <span className="text-[11px] font-semibold text-amber-700">Unsaved changes</span>
              ) : null}
            </div>
            <textarea
              id="prompt-body"
              value={editorText}
              onChange={(e) => {
                setEditorText(e.target.value);
                setValidation(null);
              }}
              placeholder={
                isLoading
                  ? "Loading…"
                  : "Paste your PASTE BLOCK here. Keep {{PLACEHOLDERS}}. Download sample for fill-in templates."
              }
              rows={18}
              spellCheck={false}
              className="ui-input h-auto min-h-[22rem] resize-y py-3 font-mono text-[12px] leading-relaxed"
            />
          </div>

          <div className="space-y-3">
            <div className="rounded-xl border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] p-3 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-jewel-ink-muted">
                Compose preview
              </p>
              <div className="grid grid-cols-2 gap-2">
                <select
                  className="ui-input text-xs"
                  value={previewJewelry}
                  onChange={(e) => setPreviewJewelry(e.target.value)}
                  disabled={parsed.type === "subject"}
                >
                  {jewelryTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="ui-btn-secondary h-9 text-xs"
                  disabled={previewMutation.isPending}
                  onClick={() => previewMutation.mutate()}
                >
                  <Eye className="size-3.5" />
                  {previewMutation.isPending ? "Preview…" : "Preview"}
                </button>
              </div>
              <input
                className="ui-input text-xs"
                placeholder="Optional Studio add-on for preview"
                value={previewAddon}
                onChange={(e) => setPreviewAddon(e.target.value)}
              />
              <pre className="max-h-[16rem] overflow-auto rounded-lg bg-white p-2 text-[11px] font-mono whitespace-pre-wrap text-jewel-ink">
                {preview?.final_prompt || preview?.prompt || "Run Preview to see the composed prompt."}
              </pre>
            </div>

            {validation ? (
              <div
                className={`rounded-xl border p-3 text-xs space-y-1 ${
                  validation.ok
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-rose-200 bg-rose-50 text-rose-900"
                }`}
              >
                <p className="font-semibold">
                  {validation.ok ? "Validation passed" : "Validation errors"} ·{" "}
                  {validation.char_count} chars
                </p>
                {validation.errors.map((e) => (
                  <p key={e}>• {e}</p>
                ))}
                {validation.warnings.map((w) => (
                  <p key={w} className="text-amber-800">
                    ⚠ {w}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        </div>

        {showVersions && entityId ? (
          <div className="rounded-xl border border-[var(--jewel-border)] p-3 space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-jewel-ink-muted">
              Version history
            </p>
            <ul className="max-h-48 space-y-1 overflow-y-auto">
              {versions.map((v) => (
                <li
                  key={v.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--jewel-hairline)] px-2 py-1.5 text-xs"
                >
                  <span>
                    v{v.version}
                    {v.is_active ? (
                      <span className="ml-2 font-semibold text-[var(--jewel-accent)]">active</span>
                    ) : null}
                  </span>
                  <span className="flex gap-1">
                    <button
                      type="button"
                      className="ui-btn-secondary h-7 px-2 text-[10px]"
                      onClick={() => setDiffAgainst(v)}
                    >
                      Diff
                    </button>
                    {!v.is_active ? (
                      <button
                        type="button"
                        className="ui-btn-secondary h-7 px-2 text-[10px]"
                        disabled={activateMutation.isPending}
                        onClick={() => {
                          if (window.confirm(`Activate version ${v.version}?`)) {
                            activateMutation.mutate(v.id);
                          }
                        }}
                      >
                        Activate
                      </button>
                    ) : null}
                  </span>
                </li>
              ))}
              {!versions.length ? (
                <li className="text-jewel-ink-muted">No versions yet — save to create one.</li>
              ) : null}
            </ul>
            {diffAgainst ? (
              <div className="mt-2 max-h-56 overflow-auto rounded-lg border border-[var(--jewel-hairline)]">
                <p className="bg-[var(--jewel-surface-muted)] px-2 py-1 text-[10px] font-semibold">
                  Diff: v{diffAgainst.version} (left) vs editor (right)
                </p>
                <table className="w-full text-[10px] font-mono">
                  <tbody>
                    {diffRows.map((row, i) => (
                      <tr
                        key={i}
                        className={row.changed ? "bg-amber-50" : undefined}
                      >
                        <td className="w-1/2 border-r border-[var(--jewel-hairline)] px-1 py-0.5 align-top whitespace-pre-wrap">
                          {row.left}
                        </td>
                        <td className="w-1/2 px-1 py-0.5 align-top whitespace-pre-wrap">
                          {row.right}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--jewel-hairline)] pt-4">
          <label className="inline-flex cursor-pointer items-center gap-2 text-[12px] font-semibold text-jewel-ink-muted">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="size-4 rounded border-[var(--jewel-border)]"
            />
            Active for generation
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                runValidate().catch((err: Error) => toast.error(err.message || "Validate failed"))
              }
              className="ui-btn-secondary h-10 text-[12px]"
            >
              Validate
            </button>
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending || isLoading || !isDirty}
              aria-busy={saveMutation.isPending}
              className="ui-btn-primary h-10 min-w-[8rem]"
            >
              {saveMutation.isPending ? (
                <FacetMark variant="spin" size={14} className="text-white" />
              ) : (
                <Save className="size-3.5" />
              )}
              {saveMutation.isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
