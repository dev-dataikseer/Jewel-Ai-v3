import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Eye, ImageIcon, ImageOff, Save } from "lucide-react";
import { api } from "@/lib/api";
import type { PromptProfileV2 } from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
};

type RefMode = "without_reference" | "with_reference";

const HIDDEN_WORKFLOWS = new Set([
  "BULK_GENERATION",
  "JEWELRY_ON_MODEL",
  "CUSTOMER_TRY_ON",
  "REFERENCE_STYLE_MATCH",
]);

const HEADER_RE = /^([A-Z][A-Z0-9 /_\-]{0,80}):\s*(.*)$/;

/** Flat text → { HEADER: body } JSON. Header line becomes the key. */
export function textToContentJson(raw: string): Record<string, string> {
  const text = (raw || "").trim();
  if (!text) return {};
  const sections: Record<string, string> = {};
  let currentKey: string | null = null;
  const buf: string[] = [];

  const flush = () => {
    if (currentKey != null) {
      sections[currentKey] = buf.join("\n").trim();
    }
    currentKey = null;
    buf.length = 0;
  };

  for (const line of text.split("\n")) {
    const m = line.trim() ? line.trim().match(HEADER_RE) : null;
    if (m && m[1].length <= 80) {
      flush();
      currentKey = m[1].trim();
      const rest = m[2] || "";
      if (rest) buf.push(rest);
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

/** { HEADER: body } → flat text for the editor. */
export function contentJsonToText(content: Record<string, string> | null | undefined): string {
  if (!content || typeof content !== "object") return "";
  return Object.entries(content)
    .filter(([, v]) => (v || "").trim())
    .map(([k, v]) => {
      const body = String(v).trim();
      if (body.toUpperCase().startsWith(`${k.toUpperCase()}:`)) return body;
      return `${k}: ${body}`;
    })
    .join("\n\n");
}

type AssembleResult = {
  final_prompt?: string;
  prompt?: string;
  negative_prompt?: string | null;
  reference_mode?: string;
  composePath?: string;
};

/** Prompt Studio: Without / With reference + one plain text box. Save → JSON. */
export function PromptStudio({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const visibleWorkflows = useMemo(
    () => workflows.filter((w) => !HIDDEN_WORKFLOWS.has(w.id)),
    [workflows],
  );

  const [workflow, setWorkflow] = useState(visibleWorkflows[0]?.id || "CATALOG_IMAGE");
  const [refMode, setRefMode] = useState<RefMode>("without_reference");
  const [editorText, setEditorText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<AssembleResult | null>(null);
  const [previewJewelry, setPreviewJewelry] = useState(jewelryTypes[0] || "Ring");

  const { data: profile, isLoading } = useQuery({
    queryKey: ["prompt-profile", workflow, refMode],
    staleTime: 60_000,
    queryFn: async () =>
      (await api.get<PromptProfileV2>(`/prompts/profiles/${workflow}/${refMode}`)).data,
  });

  useEffect(() => {
    if (!profile) return;
    let text = contentJsonToText(profile.content_json || {});
    const pool = profile.environment_pool;
    if (refMode === "without_reference" && Array.isArray(pool) && pool.length > 0) {
      const poolBlock = `ENVIRONMENT_POOL:\n${pool.join("\n")}`;
      text = text ? `${text}\n\n${poolBlock}` : poolBlock;
    }
    setEditorText(text);
    setDirty(false);
  }, [profile, refMode]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const parsed = textToContentJson(editorText);
      const poolRaw = parsed.ENVIRONMENT_POOL || parsed["ENVIRONMENT POOL"];
      const content = { ...parsed };
      delete content.ENVIRONMENT_POOL;
      delete content["ENVIRONMENT POOL"];
      const environment_pool =
        refMode === "without_reference" && poolRaw
          ? poolRaw
              .split("\n")
              .map((l) => l.trim())
              .filter(Boolean)
          : null;
      await api.put(`/prompts/profiles/${workflow}/${refMode}`, {
        content_json: content,
        environment_pool,
      });
    },
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prompt-profile", workflow, refMode] });
      toast.success("Saved (headers → JSON keys)");
    },
    onError: (err: Error) => toast.error(err.message || "Save failed"),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const withRef = refMode === "with_reference";
      return (
        await api.post<AssembleResult>("/prompts/assemble", {
          workflow,
          jewelry_type: previewJewelry,
          reference_mode: refMode,
          simulate_images: {
            product: true,
            theme: withRef,
            portrait: false,
            logo: false,
          },
        })
      ).data;
    },
    onSuccess: setPreview,
    onError: (err: Error) => toast.error(err.message || "Preview failed"),
  });

  const pageTitle =
    refMode === "without_reference" ? "Without reference" : "With reference";

  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      <div className="rounded-xl border border-[var(--jewel-border)] bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-jewel-ink">Prompt Studio</h2>
            <p className="text-xs text-jewel-ink-muted">
              Two pages. One text box. Save converts each HEADER: into JSON.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-jewel-ink-muted">
            Workflow
            <select
              value={workflow}
              onChange={(e) => {
                setWorkflow(e.target.value);
                setDirty(false);
                setPreview(null);
              }}
              className="rounded-lg border border-[var(--jewel-border)] bg-white px-2 py-1.5 text-sm font-semibold text-jewel-ink"
            >
              {visibleWorkflows.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => {
              setRefMode("without_reference");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              refMode === "without_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] bg-white hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageOff className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold text-jewel-ink">Without reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">Product image only</span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setRefMode("with_reference");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              refMode === "with_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] bg-white hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageIcon className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold text-jewel-ink">With reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">
                Style ref / portrait / logo uploaded
              </span>
            </span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_320px]">
        <section className="rounded-xl border border-[var(--jewel-border)] bg-white p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-jewel-ink">{pageTitle}</h3>
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
            One text box only. Write{" "}
            <code className="rounded bg-[var(--jewel-surface-muted)] px-1">HEADER: description</code>
            — Save stores JSON (header = key, text = value).
          </p>
          {isLoading ? (
            <p className="text-sm text-jewel-ink-muted">Loading…</p>
          ) : (
            <textarea
              value={editorText}
              onChange={(e) => {
                setEditorText(e.target.value);
                setDirty(true);
              }}
              rows={24}
              spellCheck={false}
              className="w-full resize-y rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] px-3 py-2 font-mono text-[13px] leading-relaxed text-jewel-ink"
              placeholder={"ROLE: …\n\nCAMERA: …\n\nLIGHTING: …\n\nNEGATIVE PROMPT: …"}
            />
          )}
        </section>

        <aside className="rounded-xl border border-[var(--jewel-border)] bg-white p-3 flex flex-col gap-3 max-h-[80vh]">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-[var(--jewel-accent)]" />
            <h3 className="text-sm font-semibold">Preview</h3>
          </div>
          <label className="text-[11px] font-medium text-jewel-ink-muted">
            Jewelry
            <select
              value={previewJewelry}
              onChange={(e) => setPreviewJewelry(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[var(--jewel-border)] px-2 py-1.5 text-sm"
            >
              {jewelryTypes.map((jt) => (
                <option key={jt} value={jt}>
                  {jt}
                </option>
              ))}
            </select>
          </label>
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
              <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-jewel-ink-muted">
                {preview.composePath || "compose"} · {preview.reference_mode || refMode}
              </p>
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-jewel-ink">
                {preview.final_prompt || preview.prompt || "(empty)"}
              </pre>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
