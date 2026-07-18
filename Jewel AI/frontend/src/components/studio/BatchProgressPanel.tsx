import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, Layers3, X } from "lucide-react";
import { api, mediaUrl } from "@/lib/api";
import type { BatchOut, Job } from "@/types";

type Props = {
  batchId: string;
  activeJobId: string | null;
  onSelectJob: (jobId: string) => void;
  onDismiss: () => void;
  queueModeWarning?: boolean;
};

function statusLabel(status: string) {
  switch (status) {
    case "COMPLETED":
      return "Done";
    case "FAILED":
      return "Failed";
    case "CANCELLED":
      return "Cancelled";
    case "PROCESSING":
      return "Running";
    case "PENDING":
      return "Queued";
    default:
      return status;
  }
}

function statusClass(status: string) {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-500";
    case "FAILED":
      return "bg-rose-500";
    case "CANCELLED":
      return "bg-slate-400";
    case "PROCESSING":
      return "bg-blue-500";
    default:
      return "bg-amber-400";
  }
}

export function BatchProgressPanel({
  batchId,
  activeJobId,
  onSelectJob,
  onDismiss,
  queueModeWarning,
}: Props) {
  const queryClient = useQueryClient();

  const { data: batch } = useQuery({
    queryKey: ["batch", batchId],
    queryFn: async () => (await api.get<BatchOut>(`/jobs/batches/${batchId}`)).data,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "PENDING" || s === "PROCESSING" ? 2500 : false;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () =>
      (await api.post<BatchOut>(`/jobs/batches/${batchId}/cancel`)).data,
    onSuccess: (updated) => {
      queryClient.setQueryData(["batch", batchId], updated);
      queryClient.invalidateQueries({ queryKey: ["recent-jobs"] });
      toast.message("Batch cancelled");
    },
    onError: () => toast.error("Could not cancel batch"),
  });

  const zipMutation = useMutation({
    mutationFn: async () => {
      const res = await api.get(`/jobs/batches/${batchId}/zip`, {
        responseType: "blob",
      });
      return res.data as Blob;
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `batch-${batchId.slice(0, 8)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("ZIP downloaded");
    },
    onError: () => toast.error("ZIP download failed"),
  });

  if (!batch) {
    return (
      <div className="ui-card p-4 text-xs text-slate-500">Loading batch…</div>
    );
  }

  const jobs = (batch.jobs || []) as Job[];
  const total = batch.total_jobs || jobs.length || 1;
  const done = batch.completed_jobs || 0;
  const failed = batch.failed_jobs || 0;
  const pct = Math.round((done / total) * 100);
  const active =
    batch.status === "PENDING" || batch.status === "PROCESSING";
  const canZip =
    batch.status === "COMPLETED" ||
    batch.status === "COMPLETED_WITH_ERRORS" ||
    done > 0;

  return (
    <div className="ui-card space-y-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="ui-label mb-0 flex items-center gap-1.5">
            <Layers3 className="size-3.5" /> Batch progress
          </p>
          <p className="mt-1 text-xs text-slate-600">
            {done}/{total} done
            {failed ? ` · ${failed} failed` : ""}
            {" · "}
            <span className="font-semibold text-slate-800">{batch.status}</span>
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label="Dismiss batch panel"
        >
          <X className="size-3.5" />
        </button>
      </div>

      {queueModeWarning && active && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[11px] text-amber-900">
          Running inline (no worker). Progress may reset if the API restarts.
        </p>
      )}

      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full bg-blue-600 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {jobs.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {jobs.map((job, i) => {
            const thumb = job.output_url || job.input_url;
            const selected = activeJobId === job.id;
            return (
              <button
                key={job.id}
                type="button"
                onClick={() => onSelectJob(job.id)}
                className={`relative size-14 shrink-0 overflow-hidden rounded-lg border ${
                  selected
                    ? "border-blue-600 ring-2 ring-blue-500/25"
                    : "border-slate-200"
                }`}
                title={`Job ${i + 1}: ${statusLabel(job.status)}`}
              >
                {thumb ? (
                  <img
                    src={mediaUrl(thumb)}
                    alt=""
                    className="size-full object-cover"
                  />
                ) : (
                  <div className="flex size-full items-center justify-center bg-slate-100 text-[9px] font-semibold text-slate-500">
                    {i + 1}
                  </div>
                )}
                <span
                  className={`absolute bottom-0.5 left-0.5 rounded px-1 py-px text-[8px] font-bold text-white ${statusClass(job.status)}`}
                >
                  {statusLabel(job.status)}
                </span>
              </button>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {active && (
          <button
            type="button"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
            className="ui-btn-secondary h-8 px-3 text-xs text-rose-700 border-rose-200 hover:bg-rose-50"
          >
            Cancel all
          </button>
        )}
        {canZip && (
          <button
            type="button"
            onClick={() => zipMutation.mutate()}
            disabled={zipMutation.isPending}
            className="ui-btn-secondary h-8 px-3 text-xs"
          >
            <Download className="size-3.5" />
            {zipMutation.isPending ? "Preparing…" : "Download ZIP"}
          </button>
        )}
      </div>
    </div>
  );
}
