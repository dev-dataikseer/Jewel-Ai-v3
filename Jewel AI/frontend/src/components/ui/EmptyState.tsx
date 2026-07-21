import type { ReactNode } from "react";
import { FacetMark } from "@/components/ui/FacetMark";

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  secondaryAction?: ReactNode;
  className?: string;
  compact?: boolean;
  /** Shows a spinning indicator instead of the facet icon — for loading states */
  loading?: boolean;
};

/** Designed empty moment — icon + sentence + optional CTA. */
export function EmptyState({
  title,
  description,
  action,
  secondaryAction,
  className = "",
  compact = false,
  loading = false,
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${
        compact ? "px-4 py-8" : "px-6 py-12"
      } ${className}`}
      role={loading ? "status" : "status"}
      aria-busy={loading}
    >
      <div
        className="mb-3 grid place-items-center rounded-full p-3"
        style={{
          backgroundColor: "var(--jewel-accent-soft)",
          color: "var(--jewel-accent)",
        }}
      >
        <FacetMark
          variant={loading ? "spin" : "outline"}
          size={compact ? 28 : 36}
        />
      </div>
      <p className="text-sm font-semibold text-[var(--jewel-ink)]">{title}</p>
      {description ? (
        <p className="mt-1 max-w-sm text-xs leading-relaxed text-[var(--jewel-ink-muted)]">
          {description}
        </p>
      ) : null}
      {(action || secondaryAction) && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
