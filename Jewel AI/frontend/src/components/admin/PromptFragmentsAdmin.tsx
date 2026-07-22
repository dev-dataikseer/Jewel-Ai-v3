import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { PromptVersion } from "@/types";

type FragmentRow = {
  id: string | null;
  fragment_key: string;
  name: string;
  description?: string | null;
  is_active: boolean;
  prompt_text: string | null;
  content_json?: unknown;
  active_version_id?: string | null;
};

type ValidateResult = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

const CATEGORY_ORDER: { id: string; label: string; match: (key: string) => boolean }[] = [
  { id: "lock", label: "Fidelity lock", match: (k) => k.includes("FIDELITY") },
  { id: "exec", label: "Execution modes", match: (k) => k.startsWith("EXEC_") },
  { id: "brand", label: "Branding", match: (k) => k.startsWith("BRAND_") },
  { id: "attach", label: "Attachments", match: (k) => k.startsWith("ATTACH_") },
  { id: "bg", label: "Background", match: (k) => k.startsWith("BACKGROUND_") },
  { id: "custom", label: "Custom prompt", match: (k) => k.startsWith("CUSTOM_") },
  { id: "tryon", label: "Try-on", match: (k) => k.startsWith("TRYON_") },
  { id: "multi", label: "Multi-item / user", match: (k) => k.startsWith("MULTI_") || k.startsWith("USER_") },
  { id: "env", label: "Environment pool", match: (k) => k === "ENVIRONMENT_POOL" },
];

function categoryFor(key: string): string {
  return CATEGORY_ORDER.find((c) => c.match(key))?.id || "other";
}

export function PromptFragmentsAdmin() {
  const qc = useQueryClient();
  const { data: fragments = [], isLoading } = useQuery({
    queryKey: ["prompts", "fragments"],
    queryFn: async () => (await api.get<FragmentRow[]>("/prompts/fragments")).data,
  });

  const [selectedKey, setSelectedKey] = useState<string>("");
  const [filter, setFilter] = useState("");
  const selected = useMemo(
    () => fragments.find((f) => f.fragment_key === selectedKey) || fragments[0],
    [fragments, selectedKey],
  );
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);
  const [validation, setValidation] = useState<ValidateResult | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const grouped = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = fragments.filter(
      (f) =>
        !q ||
        f.fragment_key.toLowerCase().includes(q) ||
        (f.name || "").toLowerCase().includes(q),
    );
    const map = new Map<string, FragmentRow[]>();
    for (const cat of CATEGORY_ORDER) map.set(cat.id, []);
    map.set("other", []);
    for (const f of list) {
      const id = categoryFor(f.fragment_key);
      if (!map.has(id)) map.set(id, []);
      map.get(id)!.push(f);
    }
    return map;
  }, [fragments, filter]);

  const activeKey = selected?.fragment_key || "";
  const displayText = dirty ? draft : selected?.prompt_text || "";

  const { data: versions = [], refetch: refetchVersions } = useQuery({
    queryKey: ["prompts", "fragment-versions", selected?.id],
    queryFn: async () => {
      if (!selected?.id) return [];
      return (await api.get<PromptVersion[]>(`/prompts/fragments/${selected.id}/versions`)).data;
    },
    enabled: Boolean(selected?.id) && showVersions,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!activeKey) throw new Error("No fragment selected");
      const text = dirty ? draft : selected?.prompt_text || "";
      const v = (
        await api.post<ValidateResult>("/prompts/validate", {
          prompt_text: text,
          scope: "fragment",
        })
      ).data;
      setValidation(v);
      if (!v.ok) throw new Error(v.errors.join("; ") || "Validation failed");
      await api.post("/prompts/fragments", {
        fragment_key: activeKey,
        name: selected?.name,
        prompt_text: text,
      });
    },
    onSuccess: () => {
      toast.success("Fragment saved (new version). Generation uses this text immediately.");
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["prompts", "fragments"] });
      if (showVersions) void refetchVersions();
    },
    onError: (e: Error) => toast.error(e.message || "Save failed"),
  });

  const activateMutation = useMutation({
    mutationFn: async (versionId: string) => {
      if (!selected?.id) throw new Error("No fragment id");
      await api.post(`/prompts/fragments/${selected.id}/activate/${versionId}`);
    },
    onSuccess: () => {
      toast.success("Fragment version activated");
      qc.invalidateQueries({ queryKey: ["prompts", "fragments"] });
      void refetchVersions();
    },
    onError: (e: Error) => toast.error(e.message || "Activate failed"),
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading fragments…</p>;
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">Shared prompt fragments</h3>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed max-w-2xl">
            Shared blocks used at compose time (execution modes, branding, try-on, user wrap). Edits
            create a new DB version and apply immediately. File import lives under Tools.
          </p>
        </div>
        <button
          type="button"
          className="ui-btn-secondary text-xs h-9"
          disabled={!selected?.id}
          onClick={() => setShowVersions((v) => !v)}
        >
          {showVersions ? "Hide versions" : "Versions"}
        </button>
      </div>
      <input
        className="ui-input text-xs"
        placeholder="Filter fragments…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="space-y-3 max-h-[520px] overflow-y-auto border border-slate-200 rounded-lg p-2">
          {CATEGORY_ORDER.map((cat) => {
            const items = grouped.get(cat.id) || [];
            if (!items.length) return null;
            return (
              <div key={cat.id}>
                <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-2 mb-1">
                  {cat.label}
                </p>
                {items.map((f) => (
                  <button
                    key={f.fragment_key}
                    type="button"
                    onClick={() => {
                      setSelectedKey(f.fragment_key);
                      setDirty(false);
                      setDraft(f.prompt_text || "");
                      setValidation(null);
                    }}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs mb-0.5 ${
                      (selectedKey || fragments[0]?.fragment_key) === f.fragment_key
                        ? "bg-slate-800 text-white"
                        : "hover:bg-slate-100 text-slate-700"
                    }`}
                  >
                    <span className="block truncate">{f.name}</span>
                    <span
                      className={`block truncate font-mono text-[10px] ${
                        (selectedKey || fragments[0]?.fragment_key) === f.fragment_key
                          ? "text-slate-300"
                          : "text-slate-400"
                      }`}
                    >
                      {f.fragment_key}
                    </span>
                  </button>
                ))}
              </div>
            );
          })}
        </div>
        <div className="space-y-2">
          {selected && (
            <>
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-800">{selected.name}</p>
                  <p className="text-[11px] text-slate-500 font-mono">{selected.fragment_key}</p>
                  {!selected.prompt_text && (
                    <p className="text-[11px] text-amber-600 mt-1">
                      Empty — paste text and save, or use Tools → Import from files.
                    </p>
                  )}
                </div>
                <button
                  type="button"
                  className="ui-btn-primary text-xs px-3 py-1.5"
                  disabled={saveMutation.isPending || (!dirty && !selected.prompt_text)}
                  onClick={() => {
                    if (!dirty) setDraft(selected.prompt_text || "");
                    saveMutation.mutate();
                  }}
                >
                  {saveMutation.isPending ? "Saving…" : "Save new version"}
                </button>
              </div>
              <textarea
                className="ui-input font-mono text-xs min-h-[360px] w-full"
                value={displayText}
                onChange={(e) => {
                  setDraft(e.target.value);
                  setDirty(true);
                  setValidation(null);
                }}
                onFocus={() => {
                  if (!dirty) setDraft(selected.prompt_text || "");
                }}
                spellCheck={false}
              />
              {validation ? (
                <div
                  className={`rounded-lg border p-2 text-xs ${
                    validation.ok
                      ? "border-emerald-200 bg-emerald-50"
                      : "border-rose-200 bg-rose-50"
                  }`}
                >
                  {validation.errors.map((e) => (
                    <p key={e}>• {e}</p>
                  ))}
                  {validation.warnings.map((w) => (
                    <p key={w}>⚠ {w}</p>
                  ))}
                  {validation.ok && !validation.warnings.length ? <p>Validation passed</p> : null}
                </div>
              ) : null}
              <p className="text-[11px] text-slate-400">
                Tip: keep placeholders intact (
                {"{{CHOSEN_ENVIRONMENT}}"}, {"{{BRANDING_CLAUSE}}"}, {"{{LOGO_IMAGE_INDEX}}"},{" "}
                {"{{USER_ADDITION_TEXT}}"}).
              </p>
              {showVersions && selected.id ? (
                <ul className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                  {versions.map((v) => (
                    <li
                      key={v.id}
                      className="flex items-center justify-between gap-2 text-xs px-1 py-1"
                    >
                      <span>
                        v{v.version}
                        {v.is_active ? (
                          <span className="ml-2 text-[var(--jewel-accent)] font-semibold">
                            active
                          </span>
                        ) : null}
                      </span>
                      {!v.is_active ? (
                        <button
                          type="button"
                          className="ui-btn-secondary h-7 px-2 text-[10px]"
                          onClick={() => {
                            if (window.confirm(`Activate fragment v${v.version}?`)) {
                              activateMutation.mutate(v.id);
                            }
                          }}
                        >
                          Activate
                        </button>
                      ) : null}
                    </li>
                  ))}
                  {!versions.length ? (
                    <li className="text-slate-400">No versions yet.</li>
                  ) : null}
                </ul>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
