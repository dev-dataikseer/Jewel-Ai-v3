import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Download,
  Heart,
  RefreshCcw,
  Trash2,
  X,
} from "lucide-react";
import { mediaUrl } from "@/lib/api";
import type { Job } from "@/types";
import { label, workflowLabel } from "@/types";

type Props = {
  job: Job;
  onClose: () => void;
  onToggleFavorite: (job: Job) => void;
  onDelete?: (job: Job) => void;
  onRegenerate?: (job: Job) => void;
  onRetry?: (job: Job) => void;
  actionPending?: boolean;
};

function ComparePanel({
  title,
  url,
  alt,
  emptyLabel,
  status,
  errorMessage,
}: {
  title: string;
  url?: string | null;
  alt: string;
  emptyLabel: string;
  status?: string;
  errorMessage?: string | null;
}) {
  const isPending = status === "PENDING" || status === "PROCESSING";
  const isFailed = status === "FAILED";

  return (
    <div className="flex flex-col min-h-[200px] md:min-h-[280px]">
      <span className="ui-label border-b border-slate-100 pb-2 mb-3">{title}</span>
      <div className="flex-1 flex items-center justify-center rounded-xl bg-slate-50 p-3 min-h-[180px] md:min-h-[240px]">
        {url ? (
          <img
            src={mediaUrl(url)}
            alt={alt}
            className="max-h-[50vh] max-w-full object-contain rounded-lg"
          />
        ) : isPending ? (
          <div className="text-center" aria-live="polite">
            <RefreshCcw className="size-8 text-blue-500 mx-auto animate-spin" />
            <p className="text-xs text-slate-500 font-medium mt-2">Rendering...</p>
          </div>
        ) : isFailed && errorMessage ? (
          <p className="text-xs text-rose-600 font-medium text-center px-4">{errorMessage}</p>
        ) : (
          <span className="text-xs text-slate-400">{emptyLabel}</span>
        )}
      </div>
    </div>
  );
}

export function GenerationDetailModal({
  job,
  onClose,
  onToggleFavorite,
  onDelete,
  onRegenerate,
  onRetry,
  actionPending,
}: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = `generation-modal-title-${job.id}`;

  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const subtitleParts = [
    job.jewelry_type ? label(job.jewelry_type) : null,
    date,
    job.provider_model || null,
  ].filter(Boolean);

  const hasExtraInputs = Boolean(job.reference_url || job.model_url);
  const outputUrl = job.output_url || job.output_urls?.[0];

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-[2px]"
        aria-label="Close"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white shadow-soft"
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-100 bg-white/95 backdrop-blur px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-semibold text-slate-900 truncate">
              {workflowLabel(job.workflow)}
            </h2>
            <p className="text-xs text-slate-500 mt-1 truncate">{subtitleParts.join(" · ")}</p>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="shrink-0 inline-flex size-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-800"
            aria-label="Close"
          >
            <X className="size-4" />
          </button>
        </div>

        <div className="px-5 py-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <ComparePanel title="Input" url={job.input_url} alt="Input" emptyLabel="No input image" />
            <ComparePanel
              title="Output"
              url={outputUrl}
              alt="Output"
              emptyLabel="No output yet"
              status={job.status}
              errorMessage={job.error_message}
            />
          </div>
          {hasExtraInputs && (
            <div className="mt-5 pt-5 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-5">
              <ComparePanel
                title="Reference"
                url={job.reference_url}
                alt="Reference"
                emptyLabel="No reference image"
              />
              <ComparePanel title="Model" url={job.model_url} alt="Model" emptyLabel="No model image" />
            </div>
          )}
          {job.final_prompt && (
            <div className="mt-5 pt-5 border-t border-slate-100">
              <p className="ui-label">Final prompt</p>
              <p className="text-xs text-slate-600 whitespace-pre-wrap max-h-40 overflow-y-auto leading-relaxed">
                {job.final_prompt}
              </p>
            </div>
          )}
        </div>

        <div className="sticky bottom-0 flex flex-wrap items-center gap-2 border-t border-slate-100 bg-white px-5 py-4">
          <Link to={`/?jobId=${job.id}`} className="ui-btn-primary h-9 px-4 text-xs">
            <ArrowUpRight className="size-3.5" />
            Load Studio
          </Link>
          {onRegenerate && (
            <button
              type="button"
              onClick={() => onRegenerate(job)}
              disabled={actionPending}
              className="ui-btn-secondary"
            >
              <RefreshCcw className={`size-3.5 ${actionPending ? "animate-spin" : ""}`} />
              Regenerate
            </button>
          )}
          {onRetry && (job.status === "FAILED" || job.status === "CANCELLED") && (
            <button
              type="button"
              onClick={() => onRetry(job)}
              disabled={actionPending}
              className="ui-btn-secondary"
            >
              <RefreshCcw className={`size-3.5 ${actionPending ? "animate-spin" : ""}`} />
              Retry
            </button>
          )}
          {outputUrl && (
            <a
              href={mediaUrl(outputUrl)}
              download
              target="_blank"
              rel="noreferrer"
              className="ui-btn-secondary"
            >
              <Download className="size-3.5" />
              Download Output
            </a>
          )}
          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(job)}
              className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-100"
            >
              <Trash2 className="size-3.5" />
              Delete
            </button>
          )}
          <button
            type="button"
            onClick={() => onToggleFavorite(job)}
            className="ui-btn-secondary ml-auto"
          >
            <Heart className={`size-3.5 ${job.favorite ? "fill-red-500 text-red-500" : ""}`} />
            {job.favorite ? "Favorited" : "Favorite"}
          </button>
        </div>
      </div>
    </div>
  );
}
