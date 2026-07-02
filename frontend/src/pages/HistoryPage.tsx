import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowUpRight,
  Download,
  Gem,
  History,
  RefreshCcw,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { api, mediaUrl } from "@/lib/api";
import type { Job, JobsListResponse } from "@/types";
import { label } from "@/types";

type StatusFilter = "ALL" | "COMPLETED" | "PENDING" | "FAILED" | "FAVORITES";

function statusBadgeClass(status: string) {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-500/20 text-emerald-300 border-emerald-400/25";
    case "FAILED":
      return "bg-rose-500/20 text-rose-300 border-rose-400/25";
    case "PENDING":
    case "PROCESSING":
      return "bg-amber-500/20 text-amber-300 border-amber-400/25";
    default:
      return "bg-slate-500/20 text-slate-300 border-slate-400/25";
  }
}

export function HistoryPage() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [workflowFilter, setWorkflowFilter] = useState("");

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
    refetch,
    isRefetching,
  } = useInfiniteQuery({
    queryKey: ["jobs", statusFilter, workflowFilter],
    queryFn: async ({ pageParam }) => {
      const params: Record<string, string | number | boolean> = { limit: 24 };
      if (pageParam) params.cursor = pageParam;
      if (workflowFilter) params.workflow = workflowFilter;
      if (statusFilter === "FAVORITES") params.favorites_only = true;
      else if (statusFilter !== "ALL" && statusFilter !== "PENDING") {
        params.status = statusFilter;
      }
      const res = await api.get<JobsListResponse>("/jobs", { params });
      let items = res.data.items;
      if (statusFilter === "PENDING") {
        items = items.filter((j) => j.status === "PENDING" || j.status === "PROCESSING");
      }
      return { ...res.data, items };
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  const jobs = useMemo(() => {
    const all = data?.pages.flatMap((p) => p.items) ?? [];
    return all.map((j) => ({ ...j, favorite: favSet.has(j.id) }));
  }, [data?.pages, favSet]);

  const refresh = async () => {
    try {
      await refetch();
      await queryClient.invalidateQueries({ queryKey: ["favorites"] });
      toast.success("Gallery refreshed");
    } catch (err: unknown) {
      const message = (err as { friendlyMessage?: string })?.friendlyMessage || "Could not refresh";
      toast.error(message);
    }
  };

  return (
    <AppLayout subtitle="Studio Generations">
      <main className="mx-auto max-w-[1300px] w-full px-4 lg:px-8 py-8 flex-1">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-900">Generations Gallery</h2>
            <p className="text-sm text-slate-500 mt-1">
              Browse renders and load any job back into the Studio workspace.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              aria-label="Filter by status"
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-700 outline-none focus:ring-1 focus:ring-blue-500"
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
              className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-semibold text-slate-700 outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All workflows</option>
              <option value="CATALOG_IMAGE">Catalog</option>
              <option value="JEWELRY_ON_MODEL">On Model</option>
              <option value="GEMSTONE_COLOR_CHANGE">Gemstone</option>
              <option value="CUSTOMER_TRY_ON">Try-On</option>
            </select>
            <button
              type="button"
              onClick={refresh}
              disabled={isRefetching}
              className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <RefreshCcw className={`size-3.5 ${isRefetching ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-500">
            <Gem className="size-8 animate-pulse text-blue-600 mb-3" />
            <p className="text-sm font-medium">Loading history…</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-12 text-center">
            <History className="size-8 text-slate-300 mx-auto mb-2" />
            <p className="font-semibold text-slate-600">No generations found</p>
            <Link to="/" className="text-sm text-blue-600 hover:underline mt-2 inline-block">
              Go to Studio
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
            {hasNextPage && (
              <div className="pt-8 flex justify-center">
                <button
                  type="button"
                  onClick={() => fetchNextPage()}
                  disabled={isFetchingNextPage}
                  className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  <RefreshCcw className={`size-4 ${isFetchingNextPage ? "animate-spin" : ""}`} />
                  {isFetchingNextPage ? "Loading…" : "Load More"}
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </AppLayout>
  );
}

function JobCard({ job }: { job: Job }) {
  const imageUrl = job.output_url || job.input_url;
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <div className="group relative aspect-square rounded-xl overflow-hidden bg-slate-900 border border-slate-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all">
      {imageUrl ? (
        <img
          src={mediaUrl(imageUrl)}
          alt=""
          className="absolute inset-0 w-full h-full object-contain p-2 group-hover:scale-[1.03] transition-transform duration-300"
        />
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-400">
          <RefreshCcw className="size-4 animate-spin text-blue-500 mb-1" />
          <span className="text-[10px] font-bold">Rendering…</span>
        </div>
      )}

      <span
        className={`absolute top-2 left-2 z-20 inline-flex rounded px-1.5 py-0.5 text-[8px] font-extrabold uppercase tracking-wider border ${statusBadgeClass(job.status)}`}
      >
        {job.status === "PROCESSING" ? "PENDING" : job.status}
      </span>

      <div className="absolute inset-0 bg-slate-950/80 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-between p-3 text-white z-10">
        <div className="pt-5 flex justify-between gap-1">
          <span className="rounded bg-blue-500/20 px-1.5 py-0.5 text-[8px] font-bold uppercase border border-blue-400/25 truncate">
            {label(job.workflow)}
          </span>
          <span className="text-[8px] font-bold text-slate-400">{date}</span>
        </div>
        <div className="space-y-2">
          {job.jewelry_type && (
            <p className="text-[9px] text-slate-400 truncate">{job.jewelry_type}</p>
          )}
          {job.status === "FAILED" && job.error_message && (
            <p className="text-[9px] text-rose-300 line-clamp-2">{job.error_message}</p>
          )}
          <div className="flex gap-1.5 pt-2 border-t border-slate-800/80">
            <Link
              to={`/?jobId=${job.id}`}
              className="flex-1 inline-flex h-7 items-center justify-center gap-1 rounded-md bg-white/10 hover:bg-white/20 text-[9px] font-bold"
            >
              <ArrowUpRight className="size-3" />
              Load Studio
            </Link>
            {job.output_url && (
              <a
                href={mediaUrl(job.output_url)}
                download
                target="_blank"
                rel="noreferrer"
                aria-label={`Download image for ${label(job.workflow)}`}
                className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-blue-600 hover:bg-blue-500"
              >
                <Download className="size-3" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
