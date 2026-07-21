import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, Save } from "lucide-react";
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
import type { PromptTemplate, PromptVariant, SubjectPrompt } from "@/types";

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
  }, [isLoading, parentWorkflow, childKey, childOptions, resolveEditorContent]);

  const isDirty = editorText !== loadedSnapshot;

  const saveMutation = useMutation({
    mutationFn: async () => {
      const p = parseChildKey(childKey);
      if (p.type === "master") {
        const existing = findMaster(prompts, parentWorkflow);
        await api.post("/prompts/templates", {
          name:
            existing?.name ||
            `${workflows.find((w) => w.id === parentWorkflow)?.label || parentWorkflow} Master`,
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
          (v) => v.workflow === parentWorkflow && v.variant_key === p.variantKey,
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
    onError: (err: Error & { friendlyMessage?: string }) =>
      toast.error(err.friendlyMessage || err.message || "Failed to save prompt"),
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

  return (
    <div className="ui-card overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--jewel-hairline)] bg-[var(--jewel-surface-muted)] px-5 py-4">
        <div className="min-w-0">
          <h2 className="ui-card-title">Prompts</h2>
          <p className="mt-0.5 text-[12px] text-jewel-ink-muted">
            Paste structured prompt text, then save. Download a sample first if you need the format.
          </p>
        </div>
        <button
          type="button"
          onClick={onDownloadSample}
          className="ui-btn-secondary h-9 shrink-0 text-[12px]"
        >
          <Download className="size-3.5" />
          Download sample
        </button>
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
            onChange={(e) => setEditorText(e.target.value)}
            placeholder={
              isLoading
                ? "Loading…"
                : "Paste your prompt here. Use ROLE / CAMERA / LIGHTING sections and {{PLACEHOLDERS}} as in the sample file."
            }
            rows={18}
            spellCheck={false}
            className="ui-input h-auto min-h-[22rem] resize-y py-3 font-mono text-[12px] leading-relaxed"
          />
        </div>

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
  );
}
