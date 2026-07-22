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
/** What the big text box is editing */
type ContentKind = "category" | "jewelry" | "environments" | "image_roles";

const HIDDEN_WORKFLOWS = new Set([
  "BULK_GENERATION",
  "JEWELRY_ON_MODEL",
  "CUSTOMER_TRY_ON",
  "REFERENCE_STYLE_MATCH",
]);

const HEADER_RE = /^([A-Z][A-Z0-9 /_\-]{0,80}):\s*(.*)$/;
const PLACEHOLDER_RE = /\{\{[A-Z0-9_]+\}\}/g;

/** Remove legacy {{PLACEHOLDERS}} — user never needs to manage them. */
export function stripPlaceholders(text: string): string {
  return (text || "")
    .replace(PLACEHOLDER_RE, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Flat text → { HEADER: body }. Header line = JSON key. */
export function textToContentJson(raw: string): Record<string, string> {
  const text = stripPlaceholders(raw);
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

type ImageRoleRow = {
  id: string | null;
  role: string;
  name: string;
  instruction: string;
};

/**
 * Hierarchy:
 * 1. With / Without reference
 * 2. Dropdowns: Category, Jewelry type, Content (prompt / env / image roles)
 * 3. One large text box for the selected item
 * Save: auto-detect HEADER: → JSON keys; strip {{placeholders}}
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
  const [contentKind, setContentKind] = useState<ContentKind>("category");
  const [imageRole, setImageRole] = useState("product");

  const [editorText, setEditorText] = useState("");
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<AssembleResult | null>(null);
  const [loadedKey, setLoadedKey] = useState("");

  // When switching to with_reference, env dropdown option disappears
  useEffect(() => {
    if (refMode === "with_reference" && contentKind === "environments") {
      setContentKind("category");
    }
  }, [refMode, contentKind]);

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["prompt-profile", category, refMode],
    enabled: contentKind === "category" || contentKind === "environments",
    staleTime: 60_000,
    queryFn: async () =>
      (await api.get<PromptProfileV2>(`/prompts/profiles/${category}/${refMode}`)).data,
  });

  const { data: jewelry, isLoading: jewelryLoading } = useQuery({
    queryKey: ["prompt-jewelry", category, jewelryType],
    enabled: contentKind === "jewelry",
    staleTime: 60_000,
    queryFn: async () =>
      (
        await api.get<PromptJewelryV2>(
          `/prompts/jewelry/${category}/${encodeURIComponent(jewelryType)}`,
        )
      ).data,
  });

  const { data: imageRoles = [], isLoading: rolesLoading } = useQuery({
    queryKey: ["prompt-image-roles"],
    enabled: contentKind === "image_roles",
    staleTime: 60_000,
    queryFn: async () => (await api.get<ImageRoleRow[]>(`/prompts/image-roles`)).data,
  });

  const isLoading =
    (contentKind === "category" || contentKind === "environments"
      ? profileLoading
      : false) ||
    (contentKind === "jewelry" ? jewelryLoading : false) ||
    (contentKind === "image_roles" ? rolesLoading : false);

  // Load text for current dropdown selection
  useEffect(() => {
    const key = `${refMode}|${category}|${jewelryType}|${contentKind}|${imageRole}`;
    if (contentKind === "category") {
      if (!profile) return;
      setEditorText(stripPlaceholders(contentJsonToText(profile.content_json || {})));
      setDirty(false);
      setLoadedKey(key);
      return;
    }
    if (contentKind === "environments") {
      if (!profile) return;
      const pool = profile.environment_pool || [];
      setEditorText(Array.isArray(pool) ? pool.join("\n") : "");
      setDirty(false);
      setLoadedKey(key);
      return;
    }
    if (contentKind === "jewelry") {
      if (!jewelry) return;
      setEditorText(stripPlaceholders(contentJsonToText(jewelry.content_json || {})));
      setDirty(false);
      setLoadedKey(key);
      return;
    }
    if (contentKind === "image_roles") {
      const row = imageRoles.find((r) => r.role === imageRole);
      setEditorText(row?.instruction || "");
      setDirty(false);
      setLoadedKey(key);
    }
  }, [refMode, category, jewelryType, contentKind, imageRole, profile, jewelry, imageRoles]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const cleaned = stripPlaceholders(editorText);

      if (contentKind === "category") {
        const content = textToContentJson(cleaned);
        await api.put(`/prompts/profiles/${category}/${refMode}`, {
          content_json: content,
          environment_pool: profile?.environment_pool ?? null,
        });
        return;
      }
      if (contentKind === "environments") {
        const environment_pool = cleaned
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean);
        await api.put(`/prompts/profiles/${category}/${refMode}`, {
          content_json: profile?.content_json || {},
          environment_pool,
        });
        return;
      }
      if (contentKind === "jewelry") {
        await api.put(`/prompts/jewelry/${category}/${encodeURIComponent(jewelryType)}`, {
          content_json: textToContentJson(cleaned),
        });
        return;
      }
      if (contentKind === "image_roles") {
        await api.put(`/prompts/image-roles`, {
          role: imageRole,
          instruction: cleaned,
          workflow: null,
        });
      }
    },
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prompt-profile", category, refMode] });
      queryClient.invalidateQueries({ queryKey: ["prompt-jewelry", category, jewelryType] });
      queryClient.invalidateQueries({ queryKey: ["prompt-image-roles"] });
      toast.success("Saved — headers stored as JSON (placeholders cleaned)");
    },
    onError: (err: Error) => toast.error(err.message || "Save failed"),
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      const withRef = refMode === "with_reference";
      return (
        await api.post<AssembleResult>("/prompts/assemble", {
          workflow: category,
          jewelry_type: jewelryType,
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

  const contentLabel =
    contentKind === "category"
      ? "Category prompt"
      : contentKind === "jewelry"
        ? `Jewelry · ${jewelryType}`
        : contentKind === "environments"
          ? "Environments (one per line)"
          : `Image role · ${imageRole}`;

  const selectClass =
    "w-full rounded-lg border border-[var(--jewel-border)] bg-white px-2.5 py-2 text-sm font-medium text-jewel-ink";

  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      {/* Step 1: With / Without reference */}
      <div className="rounded-xl border border-[var(--jewel-border)] bg-white px-4 py-3">
        <h2 className="text-base font-semibold text-jewel-ink">Prompt Studio</h2>
        <p className="mt-0.5 text-xs text-jewel-ink-muted">
          1) Pick reference mode → 2) Choose category / jewelry / content → 3) Edit text → Save
        </p>

        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => {
              if (dirty && !window.confirm("Discard unsaved changes?")) return;
              setRefMode("without_reference");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              refMode === "without_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageOff className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold">Without reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">Product only</span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              if (dirty && !window.confirm("Discard unsaved changes?")) return;
              setRefMode("with_reference");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              refMode === "with_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
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

        {/* Step 2: Dropdowns */}
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 border-t border-[var(--jewel-border)] pt-3">
          <label className="block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted">
            Category
            <select
              className={`mt-1 ${selectClass}`}
              value={category}
              onChange={(e) => {
                if (dirty && !window.confirm("Discard unsaved changes?")) return;
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
            Jewelry type
            <select
              className={`mt-1 ${selectClass}`}
              value={jewelryType}
              onChange={(e) => {
                if (dirty && !window.confirm("Discard unsaved changes?")) return;
                setJewelryType(e.target.value);
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
            Content
            <select
              className={`mt-1 ${selectClass}`}
              value={contentKind}
              onChange={(e) => {
                if (dirty && !window.confirm("Discard unsaved changes?")) return;
                setContentKind(e.target.value as ContentKind);
                setDirty(false);
              }}
            >
              <option value="category">Category prompt</option>
              <option value="jewelry">Jewelry prompt</option>
              {refMode === "without_reference" && (
                <option value="environments">Environments</option>
              )}
              <option value="image_roles">Image roles</option>
            </select>
          </label>

          {contentKind === "image_roles" ? (
            <label className="block text-[11px] font-bold uppercase tracking-wide text-jewel-ink-muted">
              Image role
              <select
                className={`mt-1 ${selectClass}`}
                value={imageRole}
                onChange={(e) => {
                  if (dirty && !window.confirm("Discard unsaved changes?")) return;
                  setImageRole(e.target.value);
                  setDirty(false);
                }}
              >
                {["product", "theme", "portrait", "logo"].map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <div className="flex items-end">
              <p className="text-[11px] text-jewel-ink-muted pb-2">
                {refMode === "without_reference"
                  ? "Env list available under Content → Environments"
                  : "Environments apply when no reference image"}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Step 3: One large text box */}
      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_300px]">
        <section className="rounded-xl border border-[var(--jewel-border)] bg-white p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-jewel-ink">{contentLabel}</h3>
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
            {contentKind === "environments"
              ? "One environment sentence per line. No headers needed."
              : contentKind === "image_roles"
                ? "Plain instruction. Use {index} for image number if needed."
                : "Use HEADER: text — Save auto-converts to JSON. {{placeholders}} are removed for you."}
          </p>
          {isLoading && loadedKey === "" ? (
            <p className="text-sm text-jewel-ink-muted">Loading…</p>
          ) : (
            <textarea
              value={editorText}
              onChange={(e) => {
                setEditorText(e.target.value);
                setDirty(true);
              }}
              rows={22}
              spellCheck={false}
              className="w-full resize-y rounded-lg border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] px-3 py-2 font-mono text-[13px] leading-relaxed text-jewel-ink"
              placeholder={
                contentKind === "environments"
                  ? "A matte travertine stone slab…\nDark brushed concrete…"
                  : "ROLE: …\n\nCAMERA: …\n\nLIGHTING: …"
              }
            />
          )}
        </section>

        <aside className="rounded-xl border border-[var(--jewel-border)] bg-white p-3 flex flex-col gap-3 max-h-[80vh]">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-[var(--jewel-accent)]" />
            <h3 className="text-sm font-semibold">Full assemble</h3>
          </div>
          <p className="text-[11px] text-jewel-ink-muted">
            Preview uses current category + jewelry + reference mode.
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
              <p className="mb-1 text-[10px] font-bold uppercase text-jewel-ink-muted">
                {preview.composePath || "compose"} · {preview.reference_mode || refMode}
              </p>
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
