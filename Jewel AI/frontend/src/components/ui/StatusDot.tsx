type StatusDotProps = {
  tone?: "ok" | "warn" | "danger" | "neutral";
  className?: string;
  title?: string;
};

/** Consistent health/status indicator — emerald / amber / rose. */
export function StatusDot({ tone = "neutral", className = "", title }: StatusDotProps) {
  const toneClass =
    tone === "ok"
      ? "ui-status-dot--ok"
      : tone === "warn"
        ? "ui-status-dot--warn"
        : tone === "danger"
          ? "ui-status-dot--danger"
          : "";
  return <span className={`ui-status-dot ${toneClass} ${className}`.trim()} title={title} aria-hidden={!title} />;
}
