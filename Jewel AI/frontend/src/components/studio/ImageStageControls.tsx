import { Download, Expand, Minus, Plus } from "lucide-react";

type Props = {
  zoom: number;
  onZoomChange: (z: number) => void;
  onFullscreen?: () => void;
  downloadUrl?: string | null;
  mediaUrl?: (url: string) => string;
  /** `bar` = fill a footer strip; `overlay` = float over the image */
  variant?: "overlay" | "bar";
};

/** Zoom − / % / + and fullscreen or download. */
export function ImageStageControls({
  zoom,
  onZoomChange,
  onFullscreen,
  downloadUrl,
  mediaUrl,
  variant = "overlay",
}: Props) {
  const pct = Math.round(zoom * 100);
  const shell =
    variant === "bar"
      ? "absolute inset-0 flex items-center justify-between px-3"
      : "absolute bottom-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10";

  return (
    <div className={shell}>
      <div
        className={`inline-flex items-center gap-0.5 rounded-lg border border-[var(--jewel-border)] bg-white/95 px-1 py-0.5 shadow-sm ${
          variant === "overlay" ? "pointer-events-auto" : ""
        }`}
      >
        <button
          type="button"
          className="p-1.5 text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)] rounded"
          aria-label="Zoom out"
          onClick={() => onZoomChange(Math.max(0.5, Math.round((zoom - 0.1) * 10) / 10))}
        >
          <Minus className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onZoomChange(1)}
          title="Click to reset zoom to 100%"
          className="min-w-[2.5rem] text-center text-[11px] font-semibold tabular-nums text-[var(--jewel-ink)] hover:text-[var(--jewel-accent)] hover:underline"
        >
          {pct}%
        </button>
        <button
          type="button"
          className="p-1.5 text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)] rounded"
          aria-label="Zoom in"
          onClick={() => onZoomChange(Math.min(2, Math.round((zoom + 0.1) * 10) / 10))}
        >
          <Plus className="size-3.5" />
        </button>
      </div>
      {onFullscreen ? (
        <button
          type="button"
          className={`p-2 rounded-lg border border-[var(--jewel-border)] bg-white/95 text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)] shadow-sm ${
            variant === "overlay" ? "pointer-events-auto" : ""
          }`}
          aria-label="Fullscreen"
          onClick={onFullscreen}
        >
          <Expand className="size-3.5" />
        </button>
      ) : downloadUrl && mediaUrl ? (
        <a
          href={mediaUrl(downloadUrl)}
          download
          target="_blank"
          rel="noreferrer"
          className={`p-2 rounded-lg border border-[var(--jewel-border)] bg-white/95 text-[var(--jewel-ink-muted)] hover:text-[var(--jewel-ink)] shadow-sm ${
            variant === "overlay" ? "pointer-events-auto" : ""
          }`}
          aria-label="Download"
        >
          <Download className="size-3.5" />
        </a>
      ) : null}
    </div>
  );
}
