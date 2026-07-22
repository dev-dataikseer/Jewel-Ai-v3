import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ChevronDown, Eye, ImageIcon, ImageOff, Save } from "lucide-react";
import { api } from "@/lib/api";
import type { PromptJewelryV2, PromptProfileV2 } from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
};

type RefMode = "without_reference" | "with_reference";
/** Which prompt the big text box shows */
type EditTarget = "category" | "jewelry" | "environments";

const HIDDEN_WORKFLOWS = new Set([
  "BULK_GENERATION",
  "JEWELRY_ON_MODEL",
  "CUSTOMER_TRY_ON",
  "REFERENCE_STYLE_MATCH",
]);

const HEADER_RE = /^([A-Z][A-Z0-9 /_\-]{0,80}):\s*(.*)$/;
const PLACEHOLDER_RE = /\{\{[A-Z0-9_]+\}\}/g;

export function stripPlaceholders(text: string): string {
  return (text || "")
    .replace(PLACEHOLDER_RE, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function textToContentJson(raw: string): Record<string, string> {
  const text = stripPlaceholders(raw);
  if (!text) return {};
  const sections: Record<string, string> = {};
  let currentKey: string | null = null;
  const buf: string[] = [];

  const flush = () => {
    if (currentKey != null) sections[currentKey] = buf.join("\n").trim();
    currentKey = null;
    buf.length = 0;
  };

  for (const line of text.split("\n")) {
    const m = line.trim() ? line.trim().match(HEADER_RE) : null;
    if (m && m[1].length <= 80) {
      flush();
      currentKey = m[1].trim();
      if (m[2]) buf.push(m[2]);
    } else {
      if (currentKey == null) currentKey = "BODY";
      buf.push(line);
    }
  }
  flush();
  return Object.fromEntries(
    Object.entries(sections).filter(([, v]) => (v || "").trim().length > 0),
  );
}

export function contentJsonToText(content: Record<string, string> | null | undefined): string {
  if (!content || typeof content !== "object") return "";
  return Object.entries(content)
    .filter(([, v]) => (v || "").trim())
    .map(([k, v]) => {
      const body = stripPlaceholders(String(v));
      if (!body) return "";
      if (body.toUpperCase().startsWith(`${k.toUpperCase()}:`)) return body;
      return `${k}: ${body}`;
    })
    .filter(Boolean)
    .join("\n\n");
}

type AssembleResult = {
  final_prompt?: string;
  prompt?: string;
  negative_prompt?: string | null;
  reference_mode?: string;
  composePath?: string;
};

/**
 * Hierarchy: workflow → reference mode → jewelry type → editor → preview/save
 */
export function PromptStudio({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const visibleWorkflows = useMemo(
    () => workflows.filter((w) => !HIDDEN_WORKFLOWS.has(w.id)),
    [workflows],
  );

  const [category, setCategory] = useState(visibleWorkflows[0]?.id || "CATALOG_IMAGE");
  const [refMode, setRefMode] = useState<RefMode>("without_reference");
  const [jewelryType, setJewelryType] = useState(jewelryTypes[0] || "Ring");
  // Default to jewelry so picking a type immediately shows its prompt
  const [editTarget, setEditTarget] = useState<EditTarget>("jewelry");

  const [editorText, setEditorText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<AssembleResult | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    if (refMode === "with_reference" && editTarget === "environments") {
      setEditTarget("category");
    }
  }, [refMode, editTarget]);

  const { data: profile, isFetching: profileFetching } = useQuery({
    queryKey: ["prompt-profile", category, refMode],
    staleTime: 30_000,
    queryFn: async () =>
      (await api.get<PromptProfileV2>(`/prompts/profiles/${category}/${refMode}`)).data,
  });

  const { data: jewelry, isFetching: jewelryFetching } = useQuery({
    queryKey: ["prompt-jewelry", category, jewelryType],
    staleTime: 30_000,
    queryFn: async () =>
      (
        await api.get<PromptJewelryV2>(
          `/prompts/jewelry/${category}/${encodeURIComponent(jewelryType)}`,
        )
      ).data,
  });

  const loading =
    (editTarget === "category" || editTarget === "environments"
      ? profileFetching && !profile
      : false) || (editTarget === "jewelry" ? jewelryFetching && !jewelry : false);

  // Load text whenever selection changes
  useEffect(() => {
    if (dirty) return; // don't clobber while editing

    if (editTarget === "category") {
      if (!profile) {
        setEditorText("");
        return;
      }
      setEditorText(stripPlaceholders(contentJsonToText(profile.content_json || {})));
      return;
    }
    if (editTarget === "environments") {
      if (!profile) {
        setEditorText("");
        return;
      }
      const pool = profile.environment_pool || [];
      setEditorText(Array.isArray(pool) ? pool.join("\n") : "");
      return;
    }
    if (editTarget === "jewelry") {
      if (!jewelry) {
        setEditorText(jewelryFetching ? "" : "(No jewelry prompt saved yet — write one and Save)");
        return;
      }
      const text = stripPlaceholders(contentJsonToText(jewelry.content_json || {}));
      setEditorText(text || "(Empty jewelry prompt — write HEADER: text and Save)");
    }
  }, [editTarget, profile, jewelry, jewelryFetching, dirty, category, jewelryType, refMode]);

  const confirmLeave = () => {
    if (!dirty) return true;
    return window.confirm("You have unsaved changes. Discard them?");
  };

  const clearSelectionSideEffects = () => {
    setDirty(false);
    setPreview(null);
  };

  const switchWorkflow = (next: string) => {
    if (next === category) return;
    if (!confirmLeave()) return;
    setCategory(next);
    clearSelectionSideEffects();
  };

  const switchRef = (mode: RefMode) => {
    if (mode === refMode) return;
    if (!confirmLeave()) return;
    setRefMode(mode);
    clearSelectionSideEffects();
  };

  const switchJewelry = (next: string) => {
    if (next === jewelryType) return;
    if (!confirmLeave()) return;
    setJewelryType(next);
    setEditTarget("jewelry");
    clearSelectionSideEffects();
  };

  const switchEditTarget = (next: EditTarget) => {
    if (next === editTarget) return;
    if (!confirmLeave()) return;
    setEditTarget(next);
    setDirty(false);
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const cleaned = stripPlaceholders(editorText)
        .replace(/^\(No jewelry prompt.*\)$/m, "")
        .replace(/^\(Empty jewelry prompt.*\)$/m, "")
        .trim();

      if (editTarget === "category") {
        await api.put(`/prompts/profiles/${category}/${refMode}`, {
          content_json: textToContentJson(cleaned),
          environment_pool: profile?.environment_pool ?? null,
        });
        return;
      }
      if (editTarget === "environments") {
        await api.put(`/prompts/profiles/${category}/${refMode}`, {
          content_json: profile?.content_json || {},
          environment_pool: cleaned
            .split("\n")
            .map((l) => l.trim())
            .filter(Boolean),
        });
        return;
      }
      // jewelry
      await api.put(`/prompts/jewelry/${category}/${encodeURIComponent(jewelryType)}`, {
        content_json: textToContentJson(cleaned),
      });
    },
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prompt-profile", category, refMode] });
      queryClient.invalidateQueries({ queryKey: ["prompt-jewelry", category, jewelryType] });
      toast.success(`Saved ${editTarget} prompt`);
    },
    onError: (err: Error) => toast.error(err.message || "Save failed"),
  });

  const previewMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<AssembleResult>("/prompts/assemble", {
          workflow: category,
          jewelry_type: jewelryType,
          reference_mode: refMode,
          simulate_images: {
            product: true,
            theme: refMode === "with_reference",
            portrait: false,
            logo: false,
          },
        })
      ).data,
    onSuccess: (data) => {
      setPreview(data);
      setPreviewOpen(true);
    },
    onError: (err: Error) => toast.error(err.message || "Preview failed"),
  });

  const workflowLabel =
    visibleWorkflows.find((w) => w.id === category)?.label || category;

  const boxTitle =
    editTarget === "category"
      ? `Category prompt · ${workflowLabel}`
      : editTarget === "jewelry"
        ? `Jewelry prompt · ${jewelryType}`
        : "Environments (one line each)";

  const selectClass =
    "mt-1.5 w-full rounded-lg border border-[var(--jewel-border)] bg-white px-2.5 py-2 text-sm font-semibold text-jewel-ink transition-[border-color,box-shadow] duration-150 focus-visible:border-[var(--jewel-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/25";

  const stepLabel =
    "block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted";

  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      {/* Context selectors: workflow → reference → jewelry → edit target */}
      <div className="ui-card space-y-4 p-4 sm:p-5">
        <div>
          <h2 className="text-base font-semibold text-jewel-ink">Prompt Studio</h2>
          <p className="mt-0.5 text-xs text-jewel-ink-muted">
            Workflow → reference → jewelry type → edit → preview / save
          </p>
        </div>

        {/* 1) Workflow */}
        <label className={stepLabel}>
          1. Workflow
          <select
            className={selectClass}
            value={category}
            onChange={(e) => switchWorkflow(e.target.value)}
          >
            {visibleWorkflows.map((w) => (
              <option key={w.id} value={w.id}>
                {w.label}
              </option>
            ))}
          </select>
        </label>

        {/* 2) Reference mode */}
        <div>
          <p className={stepLabel}>2. Reference mode</p>
          <div className="mt-1.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => switchRef("without_reference")}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-[border-color,background-color,box-shadow] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/30 ${
                refMode === "without_reference"
                  ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)] shadow-sm"
                  : "border-[var(--jewel-border)] hover:bg-[var(--jewel-surface-muted)]"
              }`}
            >
              <ImageOff className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
              <span>
                <span className="block text-sm font-semibold">Without reference</span>
                <span className="block text-[11px] text-jewel-ink-muted">Product image only</span>
              </span>
            </button>
            <button
              type="button"
              onClick={() => switchRef("with_reference")}
              className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-[border-color,background-color,box-shadow] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/30 ${
                refMode === "with_reference"
                  ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)] shadow-sm"
                  : "border-[var(--jewel-border)] hover:bg-[var(--jewel-surface-muted)]"
              }`}
            >
              <ImageIcon className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
              <span>
                <span className="block text-sm font-semibold">With reference</span>
                <span className="block text-[11px] text-jewel-ink-muted">
                  Style / portrait / logo uploaded
                </span>
              </span>
            </button>
          </div>
        </div>

        {/* 3) Jewelry + what to edit */}
        <div className="grid grid-cols-1 gap-3 border-t border-[var(--jewel-border)] pt-4 sm:grid-cols-2">
          <label className={stepLabel}>
            3. Jewelry type
            <select
              className={selectClass}
              value={jewelryType}
              onChange={(e) => switchJewelry(e.target.value)}
            >
              {jewelryTypes.map((jt) => (
                <option key={jt} value={jt}>
                  {jt}
                </option>
              ))}
            </select>
          </label>

          <label className={stepLabel}>
            Edit target
            <select
              className={selectClass}
              value={editTarget}
              onChange={(e) => switchEditTarget(e.target.value as EditTarget)}
            >
              <option value="jewelry">Jewelry prompt ({jewelryType})</option>
              <option value="category">Category prompt</option>
              {refMode === "without_reference" && (
                <option value="environments">Environments</option>
              )}
            </select>
          </label>
        </div>
      </div>

      {/* Editor + preview */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(260px,320px)]">
        <section className="ui-card relative flex min-w-0 flex-col overflow-hidden p-0">
          {/* Sticky save / preview action bar */}
          <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 border-b border-[var(--jewel-border)] bg-[var(--jewel-surface)]/95 px-4 py-3 backdrop-blur-sm supports-[backdrop-filter]:bg-[var(--jewel-surface)]/85">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold text-jewel-ink">{boxTitle}</h3>
              <p className="mt-0.5 text-[11px] text-jewel-ink-muted">
                {editTarget === "environments"
                  ? "One environment sentence per line."
                  : "HEADER: description — Save converts to JSON and strips {{placeholders}}."}
              </p>
            </div>
            {dirty && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800 transition-opacity duration-150">
                Unsaved
              </span>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => previewMutation.mutate()}
                disabled={previewMutation.isPending}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-accent-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--jewel-accent)] transition-[opacity,transform,background-color] duration-150 hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/30 disabled:opacity-50"
              >
                <Eye className="size-3.5" />
                {previewMutation.isPending ? "Assembling…" : "Preview"}
              </button>
              <button
                type="button"
                disabled={saveMutation.isPending || !dirty}
                onClick={() => saveMutation.mutate()}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-[opacity,transform,box-shadow,background-color] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/40 ${
                  dirty
                    ? "bg-[var(--jewel-accent)] shadow-sm hover:brightness-105 active:scale-[0.98]"
                    : "bg-[var(--jewel-accent)] opacity-45"
                } disabled:cursor-not-allowed`}
              >
                <Save className="size-3.5" />
                {saveMutation.isPending ? "Saving…" : "Save"}
              </button>
            </div>
          </div>

          <div className="p-4 pt-3">
            {loading ? (
              <p className="py-8 text-sm text-jewel-ink-muted">Loading {jewelryType} prompt…</p>
            ) : (
              <textarea
                key={`${refMode}-${category}-${jewelryType}-${editTarget}`}
                value={editorText}
                onChange={(e) => {
                  setEditorText(e.target.value);
                  setDirty(true);
                }}
                rows={22}
                spellCheck={false}
                className="w-full resize-y rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] px-3.5 py-3 font-mono text-[13px] leading-[1.65] tracking-[0.01em] text-jewel-ink transition-[border-color,box-shadow] duration-150 placeholder:text-jewel-ink-muted/60 focus-visible:border-[var(--jewel-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/20"
                placeholder={
                  editTarget === "environments"
                    ? "A matte travertine stone slab…\nDark brushed concrete…"
                    : "ROLE: …\n\nCAMERA: …\n\nLIGHTING: …"
                }
              />
            )}
          </div>
        </section>

        {/* Collapsible assemble preview */}
        <aside className="ui-card flex max-h-[min(80vh,720px)] flex-col overflow-hidden p-0 xl:sticky xl:top-20">
          <button
            type="button"
            onClick={() => setPreviewOpen((o) => !o)}
            className="flex w-full items-center gap-2 px-4 py-3 text-left transition-colors duration-150 hover:bg-[var(--jewel-surface-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--jewel-accent)]/30"
            aria-expanded={previewOpen}
          >
            <Eye className="size-4 shrink-0 text-[var(--jewel-accent)]" />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-jewel-ink">Assemble preview</span>
              <span className="block truncate text-[11px] text-jewel-ink-muted">
                {workflowLabel} · {jewelryType} ·{" "}
                {refMode === "with_reference" ? "with" : "without"} ref
              </span>
            </span>
            {preview && !previewOpen && (
              <span className="rounded-full bg-[var(--jewel-accent-soft)] px-2 py-0.5 text-[10px] font-bold uppercase text-[var(--jewel-accent)]">
                Ready
              </span>
            )}
            <ChevronDown
              className={`size-4 shrink-0 text-jewel-ink-muted transition-transform duration-200 ${
                previewOpen ? "rotate-180" : "rotate-0"
              }`}
            />
          </button>

          <div
            className={`grid transition-[grid-template-rows] duration-200 ease-out ${
              previewOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="min-h-0 overflow-hidden">
              <div className="flex flex-col gap-3 border-t border-[var(--jewel-border)] px-4 py-3">
                <button
                  type="button"
                  onClick={() => previewMutation.mutate()}
                  disabled={previewMutation.isPending}
                  className="rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-accent-soft)] px-3 py-2 text-xs font-semibold text-[var(--jewel-accent)] transition-[opacity,background-color] duration-150 hover:brightness-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--jewel-accent)]/30 disabled:opacity-50"
                >
                  {previewMutation.isPending ? "Assembling…" : "Assemble preview"}
                </button>
                {preview ? (
                  <div className="min-h-0 max-h-[52vh] flex-1 overflow-y-auto rounded-lg bg-[var(--jewel-surface-muted)] p-3">
                    <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-jewel-ink">
                      {preview.final_prompt || preview.prompt || "(empty)"}
                    </pre>
                  </div>
                ) : (
                  <p className="text-[11px] text-jewel-ink-muted">
                    Run Assemble to see the composed prompt for this selection.
                  </p>
                )}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
