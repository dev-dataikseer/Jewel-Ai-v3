import { RefreshCcw, Wand2 } from "lucide-react";

type ActionDockProps = {
  label: string;
  hint?: string | null;
  batchBlocked?: boolean;
  onForceBatch?: () => void;
  onGenerate: () => void;
  generating?: boolean;
  disabled?: boolean;
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
      <button
        type="button"
        onClick={onGenerate}
        disabled={disabled || generating}
        className="ui-btn-primary shrink-0"
      >
        {generating ? (
          <RefreshCcw className="size-4 animate-spin" />
        ) : (
          <Wand2 className="size-4" />
        )}
        {bulkCount && bulkCount > 1 ? `Generate Bulk (${bulkCount})` : "Generate"}
      </button>
    </div>
  );
}
