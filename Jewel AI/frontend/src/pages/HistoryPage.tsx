import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useWindowVirtualizer } from "@tanstack/react-virtual";
import { toast } from "sonner";
import { Expand, Gem, Heart, RefreshCcw } from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { GenerationDetailModal } from "@/components/history/GenerationDetailModal";
import { EmptyState } from "@/components/ui/EmptyState";
import { FacetMark } from "@/components/ui/FacetMark";
import { api, thumbUrl } from "@/lib/api";
import type { Job, JobsListResponse } from "@/types";
import { HISTORY_WORKFLOW_FILTERS, label, workflowLabel } from "@/types";

type StatusFilter = "ALL" | "COMPLETED" | "PENDING" | "FAILED" | "FAVORITES";

function statusBadgeClass(status: string) {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "FAILED":
      return "bg-rose-50 text-rose-700 border-rose-200";
    case "PENDING":
    case "PROCESSING":
      return "bg-amber-50 text-amber-800 border-amber-200";
    default:
      return "bg-slate-50 text-slate-600 border-slate-200";
  }
}

function useGridColumns() {
  const [cols, setCols] = useState(2);
  useEffect(() => {
    const update = () => {
      const w = window.innerWidth;
      if (w >= 1024) setCols(6);
      else if (w >= 768) setCols(4);
      else if (w >= 640) setCols(3);
      else setCols(2);
    };
    update();
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, []);
  return cols;
}

export function HistoryPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [workflowFilter, setWorkflowFilter] = useState("");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const cols = useGridColumns();
  const listRef = useRef<HTMLDivElement>(null);
  const [scrollMargin, setScrollMargin] = useState(0);

  const { data: favoriteIds = [] } = useQuery({
    queryKey: ["favorites"],
    queryFn: async () => (await api.get<string[]>("/favorites")).data,
  });

  const favSet = useMemo(() => new Set(favoriteIds), [favoriteIds]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
    error,
    refetch,
    isRefetching,
  } = useInfiniteQuery({
    queryKey: ["jobs", statusFilter, workflowFilter],
    queryFn: async ({ pageParam }) => {
      const params: Record<string, string | number | boolean> = { limit: 24 };
      if (pageParam) params.cursor = pageParam;
      if (workflowFilter) params.workflow = workflowFilter;
      if (statusFilter === "FAVORITES") params.favorites_only = true;
      else if (statusFilter === "PENDING") params.status = "PENDING,PROCESSING";
      else if (statusFilter !== "ALL") params.status = statusFilter;
      const res = await api.get<JobsListResponse>("/jobs", { params });
      return res.data;
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    retry: 2,
    refetchInterval: (query) => {
      if (typeof document !== "undefined" && document.hidden) return false;
      const pages = query.state.data?.pages ?? [];
      const hasActive = pages.some((p) =>
        p.items.some((j) => j.status === "PENDING" || j.status === "PROCESSING"),
      );
      return hasActive || statusFilter === "PENDING" ? 4000 : false;
    },
  });

  const jobs = useMemo(() => {
    const all = data?.pages.flatMap((p) => p.items) ?? [];
    return all.map((j) => ({ ...j, favorite: favSet.has(j.id) }));
  }, [data?.pages, favSet]);

  const rowCount = Math.ceil(jobs.length / cols) || 0;
  const rowSize = useMemo(() => {
    if (typeof window === "undefined") return 200;
    const maxW = Math.min(window.innerWidth - 32, 1300);
    const gap = 16;
    const cell = (maxW - gap * (cols - 1)) / cols;
    return cell + gap;
  }, [cols]);

  useLayoutEffect(() => {
    if (listRef.current) {
      setScrollMargin(listRef.current.offsetTop);
    }
  }, [jobs.length, isLoading, isError]);

  const virtualizer = useWindowVirtualizer({
    count: rowCount,
    estimateSize: () => rowSize,
    overscan: 4,
    scrollMargin,
  });

  useEffect(() => {
    virtualizer.measure();
  }, [rowSize, cols, scrollMargin, virtualizer]);

  const virtualItems = virtualizer.getVirtualItems();
  useEffect(() => {
    const last = virtualItems[virtualItems.length - 1];
    if (!last || !hasNextPage || isFetchingNextPage) return;
    if (last.index >= rowCount - 3) {
      void fetchNextPage();
    }
  }, [virtualItems, hasNextPage, isFetchingNextPage, rowCount, fetchNextPage]);

  const selectedJobWithFavorite = useMemo(() => {
    if (!selectedJob) return null;
    return { ...selectedJob, favorite: favSet.has(selectedJob.id) };
  }, [selectedJob, favSet]);

  const toggleFavorite = useCallback(
    async (job: Job) => {
      const isFav = favSet.has(job.id);
      try {
        if (isFav) {
          await api.delete(`/favorites/${job.id}`);
        } else {
          await api.post(`/favorites/${job.id}`);
        }
        await queryClient.invalidateQueries({ queryKey: ["favorites"] });
        setSelectedJob((prev) =>
          prev?.id === job.id ? { ...prev, favorite: !isFav } : prev,
        );
      } catch {
        toast.error("Could not update favorite");
      }
    },
    [favSet, queryClient],
  );

  const deleteJob = useCallback(
    async (job: Job) => {
      if (!window.confirm("Delete this generation permanently?")) return;
      try {
        await api.delete(`/jobs/${job.id}`);
        setSelectedJob(null);
        await queryClient.invalidateQueries({ queryKey: ["jobs"] });
        toast.success("Generation deleted");
      } catch {
        toast.error("Could not delete generation");
      }
    },
    [queryClient],
  );

  const regenerateMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/regenerate`).then((r) => r.data),
    onSuccess: (job) => {
      setSelectedJob(job);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Regeneration started");
    },
    onError: () => toast.error("Regeneration failed"),
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: string) =>
      api.post<Job>(`/jobs/${jobId}/retry`).then((r) => r.data),
    onSuccess: (job) => {
      setSelectedJob(job);
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      toast.success("Retry queued");
    },
    onError: () => toast.error("Retry failed"),
  });

  const refresh = async () => {
    try {
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Gallery refreshed");
    } catch (err: unknown) {
      const message =
        (err as { friendlyMessage?: string })?.friendlyMessage ||
        "Could not refresh";
      toast.error(message);
    }
  };

  return (
    <AppLayout subtitle="AI Creative Suite">
      <main className="mx-auto max-w-[1300px] w-full px-4 lg:px-8 py-8 flex-1">
        <div className="mb-6">
          <div className="mb-4">
            <h2 className="ui-page-title">Generations Gallery</h2>
            <p className="ui-page-subtitle">
              Browse renders and open any job back in Studio.
            </p>
          </div>
          <div className="ui-card-muted flex flex-wrap items-center gap-2 border border-[var(--jewel-hairline)] px-3 py-2.5">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              aria-label="Filter by status"
              className="ui-input h-9 w-auto min-w-[8.5rem] text-xs"
            >
              <option value="ALL">All statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAVORITES">Favorites</option>
              <option value="PENDING">Pending</option>
              <option value="FAILED">Failed</option>
            </select>
            <select
              value={workflowFilter}
              onChange={(e) => setWorkflowFilter(e.target.value)}
              aria-label="Filter by workflow"
              className="ui-input h-9 w-auto min-w-[9rem] text-xs"
            >
              {HISTORY_WORKFLOW_FILTERS.map((w) => (
                <option key={w.id || "all"} value={w.id}>
                  {w.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={refresh}
              disabled={isRefetching}
              aria-busy={isRefetching}
              className="ui-btn-secondary"
            >
              {isRefetching ? (
                <FacetMark variant="spin" size={14} className="text-[var(--jewel-accent)]" />
              ) : (
                <RefreshCcw className="size-3.5 stroke-[1.75]" />
              )}
              {isRefetching ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        {isLoading ? (
          <EmptyState
            loading
            title="Loading history"
            description="Fetching your recent generations…"
          />
        ) : isError ? (
          <EmptyState
            title="Could not load history"
            description={
              (error as { friendlyMessage?: string })?.friendlyMessage ||
              "Check your connection and try again."
            }
            action={
              <button type="button" onClick={() => void refetch()} className="ui-btn-secondary">
                Retry
              </button>
            }
          />
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No generations found"
            description="Open Studio to create your first render."
            action={
              <Link to="/" className="ui-btn-primary">
                Open Studio
              </Link>
            }
          />
        ) : (
          <>
            <div
              ref={listRef}
              className="relative w-full"
              style={{ height: `${virtualizer.getTotalSize()}px` }}
            >
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const start = virtualRow.index * cols;
                const rowJobs = jobs.slice(start, start + cols);
                return (
                  <div
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    ref={virtualizer.measureElement}
                    className="absolute left-0 top-0 w-full"
                    style={{
                      transform: `translateY(${virtualRow.start - scrollMargin}px)`,
                    }}
                  >
                    <div
                      className="grid gap-4"
                      style={{
                        gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
                      }}
                    >
                      {rowJobs.map((job) => (
                        <JobCard
                          key={job.id}
                          job={job}
                          onOpen={() => setSelectedJob(job)}
                          onToggleFavorite={toggleFavorite}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
            {isFetchingNextPage && (
              <div className="pt-6 flex justify-center items-center gap-2 text-xs text-jewel-ink-muted">
                <FacetMark variant="spin" size={16} className="text-[var(--jewel-accent)]" />
                Loading more…
                Loading more…
              </div>
            )}
            {hasNextPage && !isFetchingNextPage && (
              <div className="pt-8 flex justify-center">
                <button
                  type="button"
                  onClick={() => fetchNextPage()}
                  className="ui-btn-secondary h-10 px-6 text-sm"
                >
                  <RefreshCcw className="size-4" />
                  Load More
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {selectedJobWithFavorite && (
        <GenerationDetailModal
          job={selectedJobWithFavorite}
          onClose={() => setSelectedJob(null)}
          onToggleFavorite={toggleFavorite}
          onDelete={deleteJob}
          onRegenerate={(job) => regenerateMutation.mutate(job.id)}
          onRetry={(job) => retryMutation.mutate(job.id)}
          actionPending={
            regenerateMutation.isPending || retryMutation.isPending
          }
        />
      )}
    </AppLayout>
  );
}

function JobCard({
  job,
  onOpen,
  onToggleFavorite,
}: {
  job: Job;
  onOpen: () => void;
  onToggleFavorite: (job: Job) => void;
}) {
  const imageUrl = job.output_url || job.input_url;
  const [imgFailed, setImgFailed] = useState(false);
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const wf = workflowLabel(job.workflow);
  const role = job.output_url ? "output" : "input";
  const alt = `${wf} ${role}`;
  const isFresh =
    job.status === "COMPLETED" &&
    Date.now() - new Date(job.created_at).getTime() < 15 * 60 * 1000;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className={`ui-card--interactive group relative aspect-square rounded-2xl overflow-hidden border bg-slate-100 shadow-sm hover:-translate-y-0.5 ${
        isFresh
          ? "border-[var(--jewel-precious)] shadow-[0_0_0_1px_color-mix(in_srgb,var(--jewel-precious)_40%,transparent)]"
          : "border-[var(--jewel-border)]"
      }`}
    >
      {imageUrl && !imgFailed ? (
        <img
          src={thumbUrl(imageUrl, 400)}
          alt={alt}
          loading="lazy"
          decoding="async"
          onError={() => setImgFailed(true)}
          className={`absolute inset-0 w-full h-full object-contain p-2 group-hover:scale-[1.03] transition-transform duration-300 ${
            job.status === "FAILED" ? "grayscale opacity-60" : ""
          }`}
        />
      ) : imageUrl && imgFailed ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-400">
          <Gem className="size-5 mb-1" />
          <span className="text-[10px] font-semibold">Image unavailable</span>
        </div>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-400">
          {job.status === "FAILED" ? (
            <FacetMark variant="outline" size={28} className="mb-1 text-[var(--jewel-danger)]" />
          ) : (
            <FacetMark variant="spin" size={28} className="mb-1" />
          )}
          <span className="text-[10px] font-semibold">
            {job.status === "FAILED" ? "Failed" : "Rendering..."}
          </span>
        </div>
      )}

      {job.status === "FAILED" && imageUrl && !imgFailed ? (
        <div className="absolute inset-0 z-[5] flex items-center justify-center pointer-events-none">
          <span
            className="grid place-items-center rounded-md p-1.5 shadow-sm"
            style={{ backgroundColor: "color-mix(in srgb, var(--jewel-danger) 92%, black)" }}
          >
            <FacetMark variant="outline" size={18} className="text-white" aria-hidden />
          </span>
        </div>
      ) : null}

      <div className="absolute top-2 left-2 z-20 flex flex-col gap-1.5 items-start">
        <span
          className={`inline-flex rounded-md px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide border backdrop-blur-sm ${statusBadgeClass(job.status)}`}
        >
          {job.status === "PROCESSING" ? "PENDING" : job.status}
        </span>
        {job.batch_id && (
          <Link
            to={`/?batchId=${job.batch_id}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex rounded-md border border-blue-200 bg-blue-50/95 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-blue-700 backdrop-blur-sm hover:bg-blue-100"
          >
            Batch
          </Link>
        )}
      </div>

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite(job);
        }}
        aria-label={job.favorite ? "Remove from favorites" : "Add to favorites"}
        className="absolute top-2 right-2 z-20 inline-flex size-7 items-center justify-center rounded-full bg-white/90 text-slate-600 border border-slate-200 shadow-sm hover:bg-white transition-colors"
      >
        {job.favorite ? (
          <span
            className="size-2.5 rounded-full"
            style={{ backgroundColor: "var(--jewel-precious)" }}
            aria-hidden
          />
        ) : (
          <Heart className="size-3.5" />
        )}
      </button>

      <div className="absolute inset-0 bg-slate-900/75 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-3 text-white z-10">
        <div className="pt-6 flex justify-between gap-1">
          <span className="rounded-md bg-blue-500/25 px-1.5 py-0.5 text-[9px] font-semibold uppercase border border-blue-300/30 truncate">
            {label(job.workflow)}
          </span>
          <span className="text-[9px] font-medium text-slate-300">{date}</span>
        </div>
        <div className="space-y-2">
          {job.jewelry_type && (
            <p className="text-[10px] text-slate-300 truncate">
              {job.jewelry_type}
            </p>
          )}
          {job.status === "FAILED" && job.error_message && (
            <p className="text-[10px] text-rose-200 line-clamp-2">
              {job.error_message}
            </p>
          )}
          <div className="flex items-center justify-center gap-1.5 pt-2 border-t border-white/15">
            <Expand className="size-3 text-blue-300" />
            <span className="text-[10px] font-semibold text-blue-100">
              Compare input &amp; output
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
