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

export function PromptFragmentsAdmin() {
  const qc = useQueryClient();
  const { data: fragments = [], isLoading } = useQuery({
    queryKey: ["prompts", "fragments"],
    queryFn: async () => (await api.get<FragmentRow[]>("/prompts/fragments")).data,
  });

  const [selectedKey, setSelectedKey] = useState<string>("");
  const selected = useMemo(
    () => fragments.find((f) => f.fragment_key === selectedKey) || fragments[0],
    [fragments, selectedKey],
  );
  const [draft, setDraft] = useState("");
  const [dirty, setDirty] = useState(false);

  const activeKey = selected?.fragment_key || "";
  const displayText = dirty ? draft : selected?.prompt_text || "";

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!activeKey) throw new Error("No fragment selected");
      await api.post("/prompts/fragments", {
        fragment_key: activeKey,
        name: selected?.name,
        prompt_text: dirty ? draft : selected?.prompt_text || "",
        content_json: selected?.fragment_key === "ENVIRONMENT_POOL" ? undefined : selected?.content_json,
      });
    },
    onSuccess: () => {
      toast.success("Fragment saved (new version)");
      setDirty(false);
      qc.invalidateQueries({ queryKey: ["prompts", "fragments"] });
    },
    onError: (e: Error) => toast.error(e.message || "Save failed"),
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading fragments…</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-slate-800">Shared prompt fragments</h3>
        <p className="text-xs text-slate-500 mt-1 leading-relaxed">
          Fidelity lock, execution modes, branding clauses, attachment maps, and the environment
          pool. Edit here — generation code only substitutes placeholders like{" "}
          <code className="text-[11px]">{"{{CHOSEN_ENVIRONMENT}}"}</code>.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <div className="space-y-1 max-h-[420px] overflow-y-auto border border-slate-200 rounded-lg p-2">
          {fragments.map((f) => (
            <button
              key={f.fragment_key}
              type="button"
              onClick={() => {
                setSelectedKey(f.fragment_key);
                setDirty(false);
                setDraft(f.prompt_text || "");
              }}
              className={`w-full text-left px-2 py-1.5 rounded text-xs ${
                (selectedKey || fragments[0]?.fragment_key) === f.fragment_key
                  ? "bg-slate-800 text-white"
                  : "hover:bg-slate-100 text-slate-700"
              }`}
            >
              {f.name}
            </button>
          ))}
        </div>
        <div className="space-y-2">
          {selected && (
            <>
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-800">{selected.name}</p>
                  <p className="text-[11px] text-slate-500 font-mono">{selected.fragment_key}</p>
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
                className="ui-input font-mono text-xs min-h-[320px] w-full"
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}
