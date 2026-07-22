import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Eye, ImageIcon, ImageOff, Save } from "lucide-react";
import { PromptSectionEditor, type SectionMap } from "@/components/admin/PromptSectionEditor";
import { api } from "@/lib/api";
import type { PromptImageRoleV2, PromptJewelryV2, PromptProfileV2 } from "@/types";

type Props = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
};

type EditorScope = "profile" | "jewelry" | "image_role";
type RefMode = "without_reference" | "with_reference";

const HIDDEN_WORKFLOWS = new Set([
  "BULK_GENERATION",
  "JEWELRY_ON_MODEL",
  "CUSTOMER_TRY_ON",
  "REFERENCE_STYLE_MATCH",
]);

type AssembleResult = {
  final_prompt?: string;
  prompt?: string;
  negative_prompt?: string | null;
  reference_mode?: string;
  composePath?: string;
};

/**
 * One-window Prompt Studio:
 * - Primary: two pages (Without reference / With reference)
 * - Secondary: jewelry type sections + image role labels
 * - No Shared fragments tab
 */
export function PromptStudio({ workflows, jewelryTypes }: Props) {
  const queryClient = useQueryClient();
  const visibleWorkflows = useMemo(
    () => workflows.filter((w) => !HIDDEN_WORKFLOWS.has(w.id)),
    [workflows],
  );

  const [workflow, setWorkflow] = useState(visibleWorkflows[0]?.id || "CATALOG_IMAGE");
  const [refMode, setRefMode] = useState<RefMode>("without_reference");
  const [scope, setScope] = useState<EditorScope>("profile");
  const [jewelryType, setJewelryType] = useState(jewelryTypes[0] || "Ring");
  const [imageRole, setImageRole] = useState("product");

  const [sections, setSections] = useState<SectionMap>({});
  const [envPoolText, setEnvPoolText] = useState("");
  const [roleInstruction, setRoleInstruction] = useState("");
  const [dirty, setDirty] = useState(false);
  const [preview, setPreview] = useState<AssembleResult | null>(null);
  const [previewJewelry, setPreviewJewelry] = useState(jewelryTypes[0] || "Ring");

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["prompt-profile", workflow, refMode],
    enabled: scope === "profile",
    staleTime: 30_000,
    queryFn: async () =>
      (await api.get<PromptProfileV2>(`/prompts/profiles/${workflow}/${refMode}`)).data,
  });

  const { data: jewelry, isLoading: jewelryLoading } = useQuery({
    queryKey: ["prompt-jewelry", workflow, jewelryType],
    enabled: scope === "jewelry",
    staleTime: 30_000,
    queryFn: async () =>
      (
        await api.get<PromptJewelryV2>(
          `/prompts/jewelry/${workflow}/${encodeURIComponent(jewelryType)}`,
        )
      ).data,
  });

  const { data: imageRoles = [] } = useQuery({
    queryKey: ["prompt-image-roles"],
    staleTime: 60_000,
    queryFn: async () => (await api.get<PromptImageRoleV2[]>(`/prompts/image-roles`)).data,
  });

  useEffect(() => {
    if (scope !== "profile" || !profile) return;
    setSections({ ...(profile.content_json || {}) });
    setEnvPoolText((profile.environment_pool || []).join("\n"));
    setDirty(false);
  }, [scope, profile]);

  useEffect(() => {
    if (scope !== "jewelry" || !jewelry) return;
    setSections({ ...(jewelry.content_json || {}) });
    setDirty(false);
  }, [scope, jewelry]);

  useEffect(() => {
    if (scope !== "image_role") return;
    const row = imageRoles.find((r) => r.role === imageRole);
    setRoleInstruction(row?.instruction || "");
    setDirty(false);
  }, [scope, imageRole, imageRoles]);

  const onSectionsChange = useCallback((next: SectionMap) => {
    setSections(next);
    setDirty(true);
  }, []);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (scope === "profile") {
        const pool =
          refMode === "without_reference"
            ? envPoolText
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean)
            : null;
        await api.put(`/prompts/profiles/${workflow}/${refMode}`, {
          content_json: sections,
          environment_pool: pool,
        });
      } else if (scope === "jewelry") {
        await api.put(`/prompts/jewelry/${workflow}/${encodeURIComponent(jewelryType)}`, {
          content_json: sections,
        });
      } else {
        await api.put(`/prompts/image-roles`, {
          role: imageRole,
          instruction: roleInstruction,
          workflow: null,
        });
      }
    },
    onSuccess: () => {
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["prompt-profile", workflow, refMode] });
      queryClient.invalidateQueries({ queryKey: ["prompt-jewelry", workflow, jewelryType] });
      queryClient.invalidateQueries({ queryKey: ["prompt-image-roles"] });
      toast.success("Saved");
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

  const loading =
    (scope === "profile" && profileLoading) || (scope === "jewelry" && jewelryLoading);

  const pageTitle =
    scope === "profile"
      ? refMode === "without_reference"
        ? "Page 1 — Without reference image"
        : "Page 2 — With reference image"
      : scope === "jewelry"
        ? `Jewelry · ${jewelryType}`
        : `Image role · ${imageRole}`;

  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      {/* Header + workflow */}
      <div className="rounded-xl border border-[var(--jewel-border)] bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold text-jewel-ink">Prompt Studio</h2>
            <p className="text-xs text-jewel-ink-muted">
              Two pages per workflow. No shared fragments. Heading = section key.
            </p>
          </div>
          <label className="flex items-center gap-2 text-xs font-medium text-jewel-ink-muted">
            Workflow
            <select
              value={workflow}
              onChange={(e) => {
                setWorkflow(e.target.value);
                setScope("profile");
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

        {/* Primary: With / Without reference pages */}
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => {
              setRefMode("without_reference");
              setScope("profile");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              scope === "profile" && refMode === "without_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] bg-white hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageOff className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold text-jewel-ink">Without reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">
                Product image only — modern catalog / generated background
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={() => {
              setRefMode("with_reference");
              setScope("profile");
              setDirty(false);
              setPreview(null);
            }}
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors ${
              scope === "profile" && refMode === "with_reference"
                ? "border-[var(--jewel-accent)] bg-[var(--jewel-accent-soft)]"
                : "border-[var(--jewel-border)] bg-white hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            <ImageIcon className="mt-0.5 size-5 shrink-0 text-[var(--jewel-accent)]" />
            <span>
              <span className="block text-sm font-semibold text-jewel-ink">With reference</span>
              <span className="block text-[11px] text-jewel-ink-muted">
                Style ref, portrait, or logo uploaded — system uses this page
              </span>
            </span>
          </button>
        </div>

        {/* Secondary scopes — not Shared fragments */}
        <div className="mt-3 flex flex-wrap gap-2 border-t border-[var(--jewel-border)] pt-3">
          <span className="self-center text-[10px] font-bold uppercase tracking-wider text-jewel-ink-muted">
            Also edit
          </span>
          <select
            value={scope === "jewelry" ? jewelryType : ""}
            onChange={(e) => {
              if (!e.target.value) return;
              setJewelryType(e.target.value);
              setScope("jewelry");
              setDirty(false);
            }}
            className="rounded-lg border border-[var(--jewel-border)] px-2 py-1.5 text-xs"
          >
            <option value="">Jewelry type…</option>
            {jewelryTypes.map((jt) => (
              <option key={jt} value={jt}>
                {jt}
              </option>
            ))}
          </select>
          <select
            value={scope === "image_role" ? imageRole : ""}
            onChange={(e) => {
              if (!e.target.value) return;
              setImageRole(e.target.value);
              setScope("image_role");
              setDirty(false);
            }}
            className="rounded-lg border border-[var(--jewel-border)] px-2 py-1.5 text-xs"
          >
            <option value="">Image role…</option>
            {["product", "theme", "portrait", "logo"].map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          {scope !== "profile" && (
            <button
              type="button"
              className="text-xs font-semibold text-[var(--jewel-accent)] underline"
              onClick={() => {
                setScope("profile");
                setDirty(false);
              }}
            >
              Back to {refMode === "without_reference" ? "Without" : "With"} reference page
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_340px]">
        {/* Editor */}
        <section className="rounded-xl border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
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

          {scope === "image_role" ? (
            <div className="space-y-2">
              <p className="text-xs text-jewel-ink-muted">
                Tells the model what each uploaded image is. Use{" "}
                <code className="rounded bg-white px-1">{"{index}"}</code> for the slot number.
              </p>
              <textarea
                value={roleInstruction}
                onChange={(e) => {
                  setRoleInstruction(e.target.value);
                  setDirty(true);
                }}
                rows={10}
                className="w-full rounded-lg border border-[var(--jewel-border)] bg-white px-3 py-2 font-mono text-[13px]"
              />
            </div>
          ) : loading ? (
            <p className="text-sm text-jewel-ink-muted">Loading…</p>
          ) : (
            <>
              <PromptSectionEditor
                sections={sections}
                onChange={onSectionsChange}
                emptyHint="Add sections like ROLE, CAMERA, LIGHTING. Each heading becomes a JSON key."
              />
              {scope === "profile" && refMode === "without_reference" && (
                <div className="mt-4 rounded-xl border border-[var(--jewel-border)] bg-white p-3">
                  <label className="mb-1 block text-xs font-semibold text-jewel-ink">
                    Environment pool (one line each)
                  </label>
                  <p className="mb-2 text-[11px] text-jewel-ink-muted">
                    Used when there is no reference image. Backend rotates these for variety.
                  </p>
                  <textarea
                    value={envPoolText}
                    onChange={(e) => {
                      setEnvPoolText(e.target.value);
                      setDirty(true);
                    }}
                    rows={5}
                    className="w-full rounded-lg border border-[var(--jewel-border)] px-3 py-2 font-mono text-[12px]"
                  />
                </div>
              )}
            </>
          )}
        </section>

        {/* Preview */}
        <aside className="rounded-xl border border-[var(--jewel-border)] bg-white p-3 flex flex-col gap-3 max-h-[80vh]">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-[var(--jewel-accent)]" />
            <h3 className="text-sm font-semibold">Preview</h3>
          </div>
          <p className="text-[11px] text-jewel-ink-muted">
            Showing the{" "}
            <strong>{refMode === "without_reference" ? "Without" : "With"} reference</strong> page
            for this workflow.
          </p>
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
                {preview.final_prompt || preview.prompt || "(empty — save a profile first)"}
              </pre>
              {preview.negative_prompt && (
                <>
                  <p className="mt-3 mb-1 text-[10px] font-bold uppercase text-red-700">Negative</p>
                  <pre className="whitespace-pre-wrap font-mono text-[11px] text-red-900/80">
                    {preview.negative_prompt}
                  </pre>
                </>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
