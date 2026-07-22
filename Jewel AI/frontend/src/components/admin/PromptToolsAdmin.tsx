import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";

export function PromptToolsAdmin() {
  const qc = useQueryClient();
  const [force, setForce] = useState(false);

  const importMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<{
          ok: boolean;
          fragments: number;
          masters: number;
          subjects: number;
          note?: string;
        }>(`/prompts/import-from-files?force=${force}`)
      ).data,
    onSuccess: (data) => {
      toast.success(
        `Legacy import done — fragments ${data.fragments}, masters ${data.masters}, subjects ${data.subjects}`,
      );
      qc.invalidateQueries({ queryKey: ["prompts"] });
      qc.invalidateQueries({ queryKey: ["prompt-profile"] });
    },
    onError: (e: Error) => toast.error(e.message || "Import failed"),
  });

  return (
    <div className="space-y-6">
      <div className="ui-card space-y-3 p-5">
        <h3 className="text-sm font-semibold text-jewel-ink">Prompt Profile V2</h3>
        <p className="max-w-2xl text-xs leading-relaxed text-jewel-ink-muted">
          Day-to-day edits belong in Prompt Studio: <strong>workflow</strong>,{" "}
          <strong>Without / With reference</strong>, and <strong>Jewelry types</strong>. There are
          no shared fragments and no <code className="text-[11px]">{"{{PLACEHOLDERS}}"}</code> —
          headings are JSON keys.
        </p>
        <p className="max-w-2xl text-xs leading-relaxed text-jewel-ink-muted">
          To migrate production masters/subjects/fragments into V2 profiles, run on the server:{" "}
          <code className="text-[11px]">python scripts/migrate_to_prompt_profiles.py</code>
        </p>
      </div>

      <details className="ui-card group overflow-hidden transition-[box-shadow] duration-150 open:shadow-sm">
        <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold text-jewel-ink transition-colors duration-150 hover:bg-[var(--jewel-surface-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--jewel-accent)]/30 [&::-webkit-details-marker]:hidden">
          <span className="flex items-center justify-between gap-3">
            <span>
              Advanced
              <span className="mt-0.5 block text-xs font-normal text-jewel-ink-muted">
                Legacy file import (deprecated)
              </span>
            </span>
            <span
              aria-hidden
              className="text-jewel-ink-muted transition-transform duration-200 group-open:rotate-180"
            >
              ▾
            </span>
          </span>
        </summary>
        <div className="space-y-3 border-t border-[var(--jewel-border)] px-5 py-4">
          <p className="max-w-2xl text-xs leading-relaxed text-jewel-ink-muted">
            Loads old <code className="text-[11px]">docs/Modals/Prompts/*.txt</code> into the legacy
            master/subject/fragment tables. Prefer Prompt Studio + the migration script above.
          </p>
          <label className="flex items-center gap-2 text-xs text-jewel-ink-muted">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="rounded border-[var(--jewel-border)]"
            />
            Force new versions even when text is unchanged
          </label>
          <button
            type="button"
            className="ui-btn-secondary h-9 text-xs"
            disabled={importMutation.isPending}
            onClick={() => {
              if (
                window.confirm(
                  force
                    ? "Force re-import from files? This may create many new versions."
                    : "Import from files (skip unchanged)?",
                )
              ) {
                importMutation.mutate();
              }
            }}
          >
            {importMutation.isPending ? "Importing…" : "Import from files (legacy)"}
          </button>
        </div>
      </details>
    </div>
  );
}
