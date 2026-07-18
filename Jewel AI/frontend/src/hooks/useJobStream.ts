import { useEffect, useRef } from "react";
import { type InfiniteData, useQueryClient } from "@tanstack/react-query";
import { api, getAccessToken } from "@/lib/api";
import type { Job, JobsListResponse } from "@/types";

const TERMINAL = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const POLL_MS = 2500;

type StreamHandlers = {
  onUpdate?: (job: Job) => void;
  onDone?: () => void;
};

function applyJobUpdate(queryClient: ReturnType<typeof useQueryClient>, job: Job, handlers: StreamHandlers) {
  handlers.onUpdate?.(job);
  queryClient.setQueryData<Job>(["job", job.id], job);
  queryClient.setQueriesData<InfiniteData<JobsListResponse>>(
    { queryKey: ["jobs"] },
    (old) => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map((page) => ({
          ...page,
          items: page.items.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
        })),
      };
    }
  );
  queryClient.setQueriesData<Job[]>({ queryKey: ["recent-jobs"] }, (old) => {
    if (!old) return old;
    const idx = old.findIndex((j) => j.id === job.id);
    if (idx === -1) return [job, ...old].slice(0, 12);
    const next = [...old];
    next[idx] = { ...next[idx], ...job };
    return next;
  });
}

async function fetchStreamToken(jobIds: string[]): Promise<string | null> {
  try {
    const res = await api.post<{ token: string }>("/jobs/stream-token", { job_ids: jobIds });
    return res.data.token;
  } catch {
    return null;
  }
}

/** One request for many jobs instead of N parallel GETs. */
async function fetchJobsBatch(jobIds: string[]): Promise<Job[]> {
  const res = await api.get<JobsListResponse>("/jobs", {
    params: { ids: jobIds.join(","), limit: Math.min(50, jobIds.length) },
  });
  return res.data.items;
}

export function useJobStream(jobIds: string[], handlers: StreamHandlers = {}) {
  const queryClient = useQueryClient();
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    const activeIds = jobIds.filter(Boolean);
    if (activeIds.length === 0) return;

    let cancelled = false;
    let source: EventSource | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    const seen = new Map<string, string>();

    const handleJob = (job: Job) => {
      const stage = String(job.provider_metadata?.progressStage ?? "");
      const key = `${job.status}:${job.output_url ?? ""}:${stage}`;
      if (seen.get(job.id) === key) return;
      seen.set(job.id, key);
      applyJobUpdate(queryClient, job, handlersRef.current);
    };

    const allTerminal = (jobs: Job[]) =>
      activeIds.every((id) => {
        const job = jobs.find((j) => j.id === id);
        return job != null && TERMINAL.has(job.status);
      });

    const pollJobs = async () => {
      if (cancelled) return;
      try {
        const results = await fetchJobsBatch(activeIds);
        for (const job of results) {
          handleJob(job);
        }
        if (allTerminal(results)) {
          handlersRef.current.onDone?.();
          if (pollTimer) clearInterval(pollTimer);
          pollTimer = null;
        }
      } catch {
        /* retry on next interval */
      }
    };

    const startPolling = () => {
      if (pollTimer) return;
      void pollJobs();
      pollTimer = setInterval(pollJobs, POLL_MS);
    };

    const connectSse = async () => {
      const token =
        getAccessToken() != null ? await fetchStreamToken(activeIds) : null;
      if (cancelled) return;

      if (!token) {
        startPolling();
        return;
      }

      const url = `/api/jobs/stream?job_ids=${encodeURIComponent(activeIds.join(","))}&stream_token=${encodeURIComponent(token)}`;
      source = new EventSource(url);

      source.addEventListener("job_update", (event) => {
        try {
          const job = JSON.parse(event.data) as Job;
          handleJob(job);
        } catch {
          /* ignore */
        }
      });

      source.addEventListener("done", () => {
        handlersRef.current.onDone?.();
        source?.close();
        source = null;
      });

      source.onerror = () => {
        source?.close();
        source = null;
        startPolling();
      };
    };

    void connectSse();

    return () => {
      cancelled = true;
      source?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [jobIds.join(","), queryClient]);
}

export function jobStatusLabel(job: Job | null | undefined): string {
  if (!job) return "";
  if (job.status === "PENDING") return "Queued in Jewel AI";
  if (job.status === "CANCELLED") return "Cancelled";
  if (job.status === "FAILED") return "Failed";
  if (job.status === "COMPLETED") return "Complete";
  const hint = job.provider_metadata?.statusHint;
  const eta = job.provider_metadata?.etaSeconds;
  const overdue = Boolean(job.provider_metadata?.etaOverdue);
  const elapsed = job.provider_metadata?.etaElapsedSeconds;
  const etaSuffix =
    typeof eta === "number" && eta > 0
      ? overdue
        ? ` (~${eta}s more — still on fal.ai)`
        : ` (~${eta}s remaining)`
      : typeof elapsed === "number" && elapsed > 0
        ? ` (${elapsed}s elapsed)`
        : "";
  if (typeof hint === "string" && hint) {
    return `${hint}${etaSuffix}`;
  }
  const stage = job.provider_metadata?.progressStage;
  if (stage === "composing_prompt") return `Building prompt…${etaSuffix}`;
  if (stage === "waiting_on_fal") return `Waiting on fal.ai…${etaSuffix}`;
  if (job.provider_metadata?.webhook_pending) return `Waiting on fal.ai…${etaSuffix}`;
  return `Generating…${etaSuffix}`;
}
