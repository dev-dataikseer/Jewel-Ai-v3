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
      <div className="ui-card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-jewel-ink">Prompt Profile V2</h3>
        <p className="text-xs text-jewel-ink-muted leading-relaxed max-w-2xl">
          Day-to-day edits belong in the left navigator: <strong>Without / With reference</strong>,{" "}
          <strong>Jewelry types</strong>, and <strong>Image roles</strong>. There are no shared
          fragments and no <code className="text-[11px]">{"{{PLACEHOLDERS}}"}</code> — headings are
          JSON keys.
        </p>
        <p className="text-xs text-jewel-ink-muted leading-relaxed max-w-2xl">
          To migrate production masters/subjects/fragments into V2 profiles, run on the server:{" "}
          <code className="text-[11px]">python scripts/migrate_to_prompt_profiles.py</code>
        </p>
      </div>

      <div className="ui-card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-jewel-ink">
          Legacy file import (deprecated)
        </h3>
        <p className="text-xs text-jewel-ink-muted leading-relaxed max-w-2xl">
          Loads old <code className="text-[11px]">docs/Modals/Prompts/*.txt</code> into the legacy
          master/subject/fragment tables. Prefer Prompt Studio + the migration script above.
        </p>
        <label className="flex items-center gap-2 text-xs text-jewel-ink-muted">
          <input
            type="checkbox"
            checked={force}
            onChange={(e) => setForce(e.target.checked)}
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
    </div>
  );
}
