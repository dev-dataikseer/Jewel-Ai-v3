import { Wand2 } from "lucide-react";
import { FacetMark } from "@/components/ui/FacetMark";

type ActionDockProps = {
  label: string;
  hint?: string | null;
  batchBlocked?: boolean;
  onForceBatch?: () => void;
  onGenerate: () => void;
  generating?: boolean;
  disabled?: boolean;
  disabledReason?: string | null;
  bulkCount?: number;
  /** sticky bottom on all breakpoints */
  className?: string;
};

/** Single primary Generate control — desktop sticky + mobile sticky. */
export function ActionDock({
  label,
  hint,
  batchBlocked,
  onForceBatch,
  onGenerate,
  generating,
  disabled,
  disabledReason,
  bulkCount,
  className = "",
}: ActionDockProps) {
  return (
    <div
      className={`ui-sticky-bar sticky bottom-3 z-20 flex items-center gap-3 rounded-jewel-lg border border-jewel-border px-4 py-3 ${className}`}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-jewel-ink">{label}</p>
        {hint && <p className="truncate text-[11px] text-jewel-ink-muted">{hint}</p>}
        {batchBlocked && onForceBatch && (
          <button
            type="button"
            onClick={onForceBatch}
            className="mt-0.5 text-[11px] font-semibold text-jewel-accent hover:underline"
          >
            Queue another batch anyway
          </button>
        )}
      </div>
      <div title={disabled && disabledReason ? disabledReason : undefined} className="inline-block shrink-0">
        <button
          type="button"
          onClick={onGenerate}
          disabled={disabled || generating}
          aria-busy={generating || undefined}
          className="ui-btn-primary shrink-0"
        >
          {generating ? (
            <FacetMark variant="spin" size={16} className="text-white" />
          ) : (
            <Wand2 className="size-4" />
          )}
          {generating
            ? "Generating…"
            : bulkCount && bulkCount > 1
              ? `Generate Bulk (${bulkCount})`
              : "Generate"}
        </button>
      </div>
    </div>
  );
}
