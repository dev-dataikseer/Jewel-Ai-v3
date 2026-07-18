import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";

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

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!activeKey) throw new Error("No fragment selected");
      await api.post("/prompts/fragments", {
        fragment_key: activeKey,
        name: selected?.name,
        prompt_text: dirty ? draft : selected?.prompt_text || "",
      });
    },
    onSuccess: () => {
      toast.success("Fragment saved (new version). Generation uses this text immediately.");
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["prompts", "fragments"] });
    },
    onError: (e: Error) => toast.error(e.message || "Save failed"),
  });

  const importMutation = useMutation({
    mutationFn: async () =>
      (await api.post<{ ok: boolean; fragments: number; masters: number; subjects: number }>(
        "/prompts/import-from-files?force=true",
      )).data,
    onSuccess: (data) => {
      toast.success(
        `Imported from files — fragments ${data.fragments}, masters ${data.masters}, subjects ${data.subjects}`,
      );
      qc.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: (e: Error) => toast.error(e.message || "Import failed"),
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
            Seeded from <code className="text-[11px]">docs/Modals/Prompts/*.txt</code>. Edit here for
            live changes, or click <strong>Re-import from files</strong> after editing the .txt
            library. Full guide: <code className="text-[11px]">docs/Modals/Prompts/HOW_TO_EDIT_PROMPTS.md</code>
          </p>
        </div>
        <button
          type="button"
          className="ui-btn text-xs px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-50"
          disabled={importMutation.isPending}
          onClick={() => {
            if (
              window.confirm(
                "Re-import all masters, jewelry types, and fragments from docs/Modals/Prompts? This creates new DB versions.",
              )
            ) {
              importMutation.mutate();
            }
          }}
        >
          {importMutation.isPending ? "Importing…" : "Re-import from files"}
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
                      Empty — run seed import or paste text and save.
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
                }}
                onFocus={() => {
                  if (!dirty) setDraft(selected.prompt_text || "");
                }}
                spellCheck={false}
              />
              <p className="text-[11px] text-slate-400">
                Tip: keep placeholders intact (
                {"{{CHOSEN_ENVIRONMENT}}"}, {"{{BRANDING_CLAUSE}}"}, {"{{LOGO_IMAGE_INDEX}}"},{" "}
                {"{{USER_ADDITION_TEXT}}"}).
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
