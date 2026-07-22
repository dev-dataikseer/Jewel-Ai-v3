import { useCallback, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

export type SectionMap = Record<string, string>;

type Props = {
  sections: SectionMap;
  onChange: (next: SectionMap) => void;
  emptyHint?: string;
};

/** Ordered JSON key→value section editor (heading = key, description = value). */
export function PromptSectionEditor({ sections, onChange, emptyHint }: Props) {
  const entries = Object.entries(sections);
  const [newKey, setNewKey] = useState("");

  const updateKey = useCallback(
    (oldKey: string, nextKey: string) => {
      const trimmed = nextKey.trim();
      if (!trimmed || trimmed === oldKey) return;
      if (trimmed in sections && trimmed !== oldKey) return;
      const next: SectionMap = {};
      for (const [k, v] of Object.entries(sections)) {
        next[k === oldKey ? trimmed : k] = v;
      }
      onChange(next);
    },
    [onChange, sections],
  );

  const updateValue = useCallback(
    (key: string, value: string) => {
      onChange({ ...sections, [key]: value });
    },
    [onChange, sections],
  );

  const removeKey = useCallback(
    (key: string) => {
      const next = { ...sections };
      delete next[key];
      onChange(next);
    },
    [onChange, sections],
  );

  const addSection = useCallback(() => {
    const key = (newKey.trim() || "NEW_SECTION").toUpperCase().replace(/\s+/g, "_");
    let unique = key;
    let i = 2;
    while (unique in sections) {
      unique = `${key}_${i++}`;
    }
    onChange({ ...sections, [unique]: "" });
    setNewKey("");
  }, [newKey, onChange, sections]);

  if (entries.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-jewel-ink-muted">
          {emptyHint || "No sections yet. Add a heading — it becomes the JSON key."}
        </p>
        <div className="flex gap-2">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="ROLE"
            className="flex-1 rounded-lg border border-[var(--jewel-border)] bg-white px-3 py-2 text-sm font-mono"
          />
          <button
            type="button"
            onClick={addSection}
            className="inline-flex items-center gap-1 rounded-lg bg-[var(--jewel-accent)] px-3 py-2 text-sm font-semibold text-white"
          >
            <Plus className="size-4" /> Add
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="rounded-xl border border-[var(--jewel-border)] bg-white p-3 shadow-sm"
        >
          <div className="mb-2 flex items-center gap-2">
            <input
              defaultValue={key}
              onBlur={(e) => updateKey(key, e.target.value)}
              className="flex-1 rounded-md border border-[var(--jewel-border)] bg-[var(--jewel-surface-muted)] px-2 py-1.5 font-mono text-xs font-bold uppercase tracking-wide text-[var(--jewel-accent)]"
              aria-label="Section heading (JSON key)"
            />
            <button
              type="button"
              onClick={() => removeKey(key)}
              className="rounded-md p-1.5 text-jewel-ink-muted hover:bg-red-50 hover:text-red-600"
              title="Remove section"
            >
              <Trash2 className="size-4" />
            </button>
          </div>
          <textarea
            value={value}
            onChange={(e) => updateValue(key, e.target.value)}
            rows={Math.min(12, Math.max(3, value.split("\n").length + 1))}
            className="w-full resize-y rounded-lg border border-[var(--jewel-border)] bg-white px-3 py-2 font-mono text-[13px] leading-relaxed text-jewel-ink"
            placeholder="Description / prompt text for this heading…"
          />
        </div>
      ))}
      <div className="flex gap-2 pt-1">
        <input
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          placeholder="New heading (e.g. LIGHTING)"
          className="flex-1 rounded-lg border border-[var(--jewel-border)] bg-white px-3 py-2 text-sm font-mono"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addSection();
            }
          }}
        />
        <button
          type="button"
          onClick={addSection}
          className="inline-flex items-center gap-1 rounded-lg border border-[var(--jewel-border)] bg-white px-3 py-2 text-sm font-semibold text-jewel-ink hover:bg-[var(--jewel-surface-muted)]"
        >
          <Plus className="size-4" /> Add section
        </button>
      </div>
    </div>
  );
}
