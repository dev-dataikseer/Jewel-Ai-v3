import { Copy, Download, Heart, ImagePlus, MoreHorizontal, RefreshCcw } from "lucide-react";
import { useState } from "react";

type ResultsTrayProps = {
  onRegenerate: () => void;
  regenerating?: boolean;
  onDownload?: string | null;
  onFavorite: () => void;
  favorited?: boolean;
  onShare: () => void;
  onUseAsReference?: () => void;
  onCopyPrompt?: () => void;
  mediaUrl: (url: string) => string;
};

/** Single-row actions for the Generated card footer. */
export function ResultsTray({
  onRegenerate,
  regenerating,
  onDownload,
  onFavorite,
  favorited,
  onShare,
  onUseAsReference,
  onCopyPrompt,
  mediaUrl,
}: ResultsTrayProps) {
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div className="flex items-center gap-1.5 w-full min-w-0">
      <button
        type="button"
        onClick={onRegenerate}
        disabled={regenerating}
        aria-label="Generate again with current settings"
        className="ui-btn-secondary h-8 shrink-0 px-2.5 text-[11px]"
      >
        <RefreshCcw className={`size-3.5 ${regenerating ? "animate-spin" : ""}`} />
        Again
      </button>
      {onDownload ? (
        <a
          href={mediaUrl(onDownload)}
          download
          target="_blank"
          rel="noreferrer"
          aria-label="Download generated image"
          className="ui-btn-primary h-8 shrink-0 px-2.5 text-[11px] whitespace-nowrap"
        >
          <Download className="size-3.5" />
          Download
        </a>
      ) : null}
      <div className="relative ml-auto shrink-0">
        <button
          type="button"
          aria-label="More actions"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((o) => !o)}
          className="ui-btn-ghost h-8 w-8 p-0"
        >
          <MoreHorizontal className="size-4" />
        </button>
        {moreOpen ? (
          <div className="absolute right-0 bottom-full z-20 mb-1 min-w-[150px] rounded-lg border border-[var(--jewel-border)] bg-white py-1 shadow-card">
            {onUseAsReference && (
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-[var(--jewel-surface-muted)]"
                onClick={() => {
                  onUseAsReference();
                  setMoreOpen(false);
                }}
              >
                <ImagePlus className="size-3.5 text-jewel-accent" />
                Use as Reference
              </button>
            )}
            {onCopyPrompt && (
              <button
                type="button"
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-[var(--jewel-surface-muted)]"
                onClick={() => {
                  onCopyPrompt();
                  setMoreOpen(false);
                }}
              >
                <Copy className="size-3.5" />
                Copy Prompt
              </button>
            )}
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-[var(--jewel-surface-muted)]"
              onClick={() => {
                onFavorite();
                setMoreOpen(false);
              }}
            >
              <Heart
                className={`size-3.5 ${
                  favorited
                    ? "fill-[var(--jewel-precious)] text-[var(--jewel-precious)]"
                    : ""
                }`}
              />
              {favorited ? "Unsave" : "Save"}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-[var(--jewel-surface-muted)]"
              onClick={() => {
                onShare();
                setMoreOpen(false);
              }}
            >
              Share
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
