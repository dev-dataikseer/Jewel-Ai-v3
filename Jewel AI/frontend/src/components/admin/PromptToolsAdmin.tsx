import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";

const PLACEHOLDER_HELP = [
  { token: "{{SUBTYPE_BLOCK}}", meaning: "Jewelry-type subject text (Ring, Necklace, …)" },
  { token: "{{EXECUTION_BLOCK}}", meaning: "Catalog execution mode (modern / mirror / mood)" },
  { token: "{{BRANDING_CLAUSE}}", meaning: "Logo / theme branding rules" },
  { token: "{{CHOSEN_ENVIRONMENT}}", meaning: "Backend-picked environment sentence" },
  { token: "{{PLACEMENT_ANATOMY}}", meaning: "Try-on placement anatomy" },
  { token: "{{TRYON_MODE_CLAUSE}}", meaning: "Studio vs customer try-on clause" },
  { token: "{{USER_INSTRUCTION}}", meaning: "Studio optional add-on (also USER_ADDITION_TEXT)" },
  { token: "{{LOGO_LABEL}}", meaning: "Logo image label / index" },
  { token: "{{THEME_LINE}}", meaning: "Optional theme attachment line" },
  { token: "{{LOGO_LINE}}", meaning: "Optional logo attachment line" },
  { token: "{{TARGET_COLOR}}", meaning: "Gemstone target color" },
  { token: "{{PRODUCT_INDEX}}", meaning: "Product image index" },
];

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
        `Import done — fragments ${data.fragments}, masters ${data.masters}, subjects ${data.subjects}`,
      );
      qc.invalidateQueries({ queryKey: ["prompts"] });
    },
    onError: (e: Error) => toast.error(e.message || "Import failed"),
  });

  return (
    <div className="space-y-6">
      <div className="ui-card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-jewel-ink">Migration / disaster recovery</h3>
        <p className="text-xs text-jewel-ink-muted leading-relaxed max-w-2xl">
          Day-to-day edits belong in <strong>Workflow prompts</strong> and{" "}
          <strong>Shared fragments</strong>. File import loads{" "}
          <code className="text-[11px]">docs/Modals/Prompts/*.txt</code> into the database when
          those files are present on the server. Prefer Admin UI for production.
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
          {importMutation.isPending ? "Importing…" : "Import from files"}
        </button>
      </div>

      <div className="ui-card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-jewel-ink">Placeholder reference</h3>
        <p className="text-xs text-jewel-ink-muted">
          Keep these tokens exactly — the engine fills them at generate time. Do not invent new{" "}
          {"{{NAMES}}"} unless registered in the backend.
        </p>
        <ul className="divide-y divide-[var(--jewel-hairline)] rounded-lg border border-[var(--jewel-border)]">
          {PLACEHOLDER_HELP.map((row) => (
            <li key={row.token} className="flex flex-col gap-0.5 px-3 py-2 sm:flex-row sm:gap-4">
              <code className="shrink-0 text-[11px] font-semibold text-[var(--jewel-accent)]">
                {row.token}
              </code>
              <span className="text-xs text-jewel-ink-muted">{row.meaning}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
