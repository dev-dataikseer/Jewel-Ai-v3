import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Download,
  Heart,
  RefreshCcw,
  X,
} from "lucide-react";
import { mediaUrl } from "@/lib/api";
import type { Job } from "@/types";
import { label, workflowLabel } from "@/types";

type Props = {
  job: Job;
  onClose: () => void;
  onToggleFavorite: (job: Job) => void;
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
      <span className="text-[11px] font-bold uppercase text-slate-400 border-b border-slate-700 pb-2 mb-3">
        {title}
      </span>
      <div className="flex-1 flex items-center justify-center rounded-xl bg-slate-950 p-3 min-h-[180px] md:min-h-[240px]">
        {url ? (
          <img
            src={mediaUrl(url)}
            alt={alt}
            className="max-h-[50vh] max-w-full object-contain rounded"
          />
        ) : isPending ? (
          <div className="text-center" aria-live="polite">
            <RefreshCcw className="size-8 text-amber-400 mx-auto animate-spin" />
            <p className="text-xs text-slate-400 font-semibold mt-2">Rendering…</p>
          </div>
        ) : isFailed && errorMessage ? (
          <p className="text-xs text-rose-400 font-medium text-center px-4">{errorMessage}</p>
        ) : (
          <span className="text-xs text-slate-500">{emptyLabel}</span>
        )}
      </div>
    </div>
  );
}

export function GenerationDetailModal({ job, onClose, onToggleFavorite }: Props) {
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
    document.addEventListener("keydown", onKeyDown);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="presentation"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/70" aria-hidden="true" />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative z-10 w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-700 bg-gray-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-700 bg-gray-900 px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-lg font-bold text-white truncate">
              {workflowLabel(job.workflow)}
            </h2>
            {subtitleParts.length > 0 && (
              <p className="text-xs text-slate-400 mt-0.5 truncate">
                {subtitleParts.join(" · ")}
              </p>
            )}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 inline-flex size-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="size-5" />
          </button>
        </div>

        {/* Error banner */}
        {job.status === "FAILED" && job.error_message && (
          <div className="mx-5 mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2.5 text-sm text-rose-300">
            {job.error_message}
          </div>
        )}

        {/* Compare body */}
        <div className="p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 divide-y md:divide-y-0 md:divide-x divide-slate-700">
            <ComparePanel
              title="Input"
              url={job.input_url}
              alt="Input"
              emptyLabel="No input image"
            />
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
            <div className="mt-5 pt-5 border-t border-slate-700 grid grid-cols-1 md:grid-cols-2 gap-5 divide-y md:divide-y-0 md:divide-x divide-slate-700">
              <ComparePanel
                title="Reference"
                url={job.reference_url}
                alt="Reference"
                emptyLabel="No reference image"
              />
              <ComparePanel
                title="Model"
                url={job.model_url}
                alt="Model"
                emptyLabel="No model image"
              />
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="sticky bottom-0 flex flex-wrap items-center gap-2 border-t border-slate-700 bg-gray-900 px-5 py-4">
          <Link
            to={`/?jobId=${job.id}`}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 px-4 text-xs font-bold text-white transition-colors"
          >
            <ArrowUpRight className="size-3.5" />
            Load Studio
          </Link>

          {job.input_url && (
            <a
              href={mediaUrl(job.input_url)}
              download
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800 hover:bg-slate-700 px-3 text-xs font-semibold text-slate-200 transition-colors"
            >
              <Download className="size-3.5" />
              Download Input
            </a>
          )}

          {outputUrl && (
            <a
              href={mediaUrl(outputUrl)}
              download
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800 hover:bg-slate-700 px-3 text-xs font-semibold text-slate-200 transition-colors"
            >
              <Download className="size-3.5" />
              Download Output
            </a>
          )}

          <button
            type="button"
            onClick={() => onToggleFavorite(job)}
            aria-label={job.favorite ? "Remove from favorites" : "Add to favorites"}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-600 bg-slate-800 hover:bg-slate-700 px-3 text-xs font-semibold text-slate-200 transition-colors ml-auto"
          >
            <Heart
              className={`size-3.5 ${job.favorite ? "fill-red-500 text-red-500" : ""}`}
            />
            {job.favorite ? "Favorited" : "Favorite"}
          </button>
        </div>
      </div>
    </div>
  );
}
