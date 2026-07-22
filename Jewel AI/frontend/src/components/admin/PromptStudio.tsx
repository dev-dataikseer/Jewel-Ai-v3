import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Eye, ImageIcon, ImageOff, Save } from "lucide-react";
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
 * Exact hierarchy:
 * 1. With / Without reference
 * 2. Category + Jewelry type + Env/Content dropdowns
 * 3. One text box showing the selected prompt
 *
 * Changing Jewelry type loads THAT jewelry prompt into the text box.
 */
export function PromptStudio({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const visibleWorkflows = useMemo(
    () => workflows.filter((w) => !HIDDEN_WORKFLOWS.has(w.id)),
    [workflows],
  );

  const [refMode, setRefMode] = useState<RefMode>("without_reference");
  const [category, setCategory] = useState(visibleWorkflows[0]?.id || "CATALOG_IMAGE");
  const [jewelryType, setJewelryType] = useState(jewelryTypes[0] || "Ring");
  // Default to jewelry so picking a type immediately shows its prompt
  const [editTarget, setEditTarget] = useState<EditTarget>("jewelry");

  const [editorText, setEditorText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<AssembleResult | null>(null);

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

  const switchRef = (mode: RefMode) => {
    if (mode === refMode) return;
    if (!confirmLeave()) return;
    setRefMode(mode);
    setDirty(false);
    setPreview(null);
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      const cleaned = stripPlaceholders(editorText).replace(
        /^\(No jewelry prompt.*\)$/m,
        "",
      ).replace(/^\(Empty jewelry prompt.*\)$/m, "").trim();

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
    onSuccess: setPreview,
    onError: (err: Error) => toast.error(err.message || "Preview failed"),
  });

  const boxTitle =
    editTarget === "category"
      ? `Category prompt · ${visibleWorkflows.find((w) => w.id === category)?.label || category}`
      : editTarget === "jewelry"
        ? `Jewelry prompt · ${jewelryType}`
        : "Environments (one line each)";

  const selectClass =
    "mt-1 w-full rounded-lg border border-[var(--jewel-border)] bg-white px-2.5 py-2 text-sm font-semibold text-jewel-ink";

  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      {/* 1) Reference mode */}
      <div className="rounded-xl border border-[var(--jewel-border)] bg-white px-4 py-3 space-y-3">
        <div>
          <h2 className="text-base font-semibold text-jewel-ink">Prompt Studio</h2>
          <p className="text-xs text-jewel-ink-muted">
            Step 1: reference → Step 2: category / jewelry / env → Step 3: edit text → Save
          </p>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => switchRef("without_reference")}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left ${
              refMode === "without_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageOff className="mt-0.5 size-5 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold">Without reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">Product image only</span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => switchRef("with_reference")}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left ${
              refMode === "with_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageIcon className="mt-0.5 size-5 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold">With reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">
                Style / portrait / logo uploaded
              </span>
            </span>
          </button>
        </div>

        {/* 2) Dropdowns — always visible after reference choice */}
        <div className="grid grid-cols-1 gap-3 border-t border-[var(--jewel-border)] pt-3 sm:grid-cols-3">
          <label className="block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted">
            1. Category
            <select
              className={selectClass}
              value={category}
              onChange={(e) => {
                if (!confirmLeave()) return;
                setCategory(e.target.value);
                setDirty(false);
              }}
            >
              {visibleWorkflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted">
            2. Jewelry type
            <select
              className={selectClass}
              value={jewelryType}
              onChange={(e) => {
                if (!confirmLeave()) return;
                setJewelryType(e.target.value);
                setEditTarget("jewelry"); // show this type's prompt immediately
                setDirty(false);
              }}
            >
              {jewelryTypes.map((jt) => (
                <option key={jt} value={jt}>
                  {jt}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted">
            3. Show in text box
            <select
              className={selectClass}
              value={editTarget}
              onChange={(e) => {
                if (!confirmLeave()) return;
                setEditTarget(e.target.value as EditTarget);
                setDirty(false);
              }}
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

      {/* 3) One text box */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_300px]">
        <section className="rounded-xl border border-[var(--jewel-border)] bg-white p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-jewel-ink">{boxTitle}</h3>
            {dirty && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-800">
                Unsaved
              </span>
            )}
            <button
              type="button"
              disabled={saveMutation.isPending || !dirty}
              onClick={() => saveMutation.mutate()}
              className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-[var(--jewel-accent)] px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              <Save className="size-3.5" />
              Save
            </button>
          </div>
          <p className="mb-2 text-[11px] text-jewel-ink-muted">
            {editTarget === "environments"
              ? "One environment sentence per line."
              : "Write HEADER: description. Save converts to JSON and removes {{placeholders}} for you."}
          </p>
          {loading ? (
            <p className="text-sm text-jewel-ink-muted py-8">Loading {jewelryType} prompt…</p>
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
              className="w-full resize-y rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] px-3 py-2 font-mono text-[13px] leading-relaxed text-jewel-ink"
              placeholder={
                editTarget === "environments"
                  ? "A matte travertine stone slab…\nDark brushed concrete…"
                  : "ROLE: …\n\nCAMERA: …\n\nLIGHTING: …"
              }
            />
          )}
        </section>

        <aside className="flex max-h-[80vh] flex-col gap-3 rounded-xl border border-[var(--jewel-border)] bg-white p-3">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-[var(--jewel-accent)]" />
            <h3 className="text-sm font-semibold">Assemble preview</h3>
          </div>
          <p className="text-[11px] text-jewel-ink-muted">
            Uses <strong>{category}</strong> + <strong>{jewelryType}</strong> +{" "}
            <strong>{refMode === "with_reference" ? "with" : "without"} reference</strong>.
          </p>
          <button
            type="button"
            onClick={() => previewMutation.mutate()}
            disabled={previewMutation.isPending}
            className="rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-accent-soft)] px-3 py-2 text-xs font-semibold text-[var(--jewel-accent)]"
          >
            {previewMutation.isPending ? "Assembling…" : "Assemble preview"}
          </button>
          {preview && (
            <div className="min-h-0 flex-1 overflow-y-auto rounded-lg bg-[var(--jewel-surface-muted)] p-2">
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed">
                {preview.final_prompt || preview.prompt || "(empty)"}
              </pre>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
