import { Download, Heart, MoreHorizontal, RefreshCcw, Columns2 } from "lucide-react";
import { useState } from "react";

type ResultsTrayProps = {
  onRegenerate: () => void;
  regenerating?: boolean;
  onDownload?: string | null;
  onFavorite: () => void;
  favorited?: boolean;
  onShare: () => void;
  compareActive?: boolean;
  onToggleCompare?: () => void;
  mediaUrl: (url: string) => string;
};

/** Post-complete actions: primary Download + Regenerate; Share/Save in overflow. */
export function ResultsTray({
  onRegenerate,
  regenerating,
  onDownload,
  onFavorite,
  favorited,
  onShare,
  compareActive,
  onToggleCompare,
  mediaUrl,
}: ResultsTrayProps) {
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {onToggleCompare && (
        <button
          type="button"
          onClick={onToggleCompare}
          aria-pressed={compareActive}
          className={`ui-btn-secondary ${compareActive ? "ui-nav-active border-transparent" : ""}`}
        >
          <Columns2 className="size-3.5" />
          Compare
        </button>
      )}
      <button
        type="button"
        onClick={onRegenerate}
        disabled={regenerating}
        aria-label="Regenerate image"
        className="ui-btn-secondary"
      >
        <RefreshCcw className={`size-3.5 ${regenerating ? "animate-spin" : ""}`} />
        Regenerate
      </button>
      {onDownload && (
        <a
          href={mediaUrl(onDownload)}
          download
          target="_blank"
          rel="noreferrer"
          aria-label="Download generated image"
          className="ui-btn-primary h-9 px-3 text-xs"
        >
          <Download className="size-3.5" />
          Download
        </a>
      )}
      <div className="relative">
        <button
          type="button"
          aria-label="More actions"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((o) => !o)}
          className="ui-btn-ghost h-9 w-9 p-0"
        >
          <MoreHorizontal className="size-4" />
        </button>
        {moreOpen && (
          <div className="absolute right-0 z-20 mt-1 min-w-[140px] rounded-jewel-md border border-jewel-border bg-jewel-surface py-1 shadow-sticky">
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-jewel-muted"
              onClick={() => {
                onFavorite();
                setMoreOpen(false);
              }}
            >
              <Heart className={`size-3.5 ${favorited ? "fill-jewel-danger text-jewel-danger" : ""}`} />
              {favorited ? "Unsave" : "Save"}
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-jewel-muted"
              onClick={() => {
                onShare();
                setMoreOpen(false);
              }}
            >
              Share link
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
