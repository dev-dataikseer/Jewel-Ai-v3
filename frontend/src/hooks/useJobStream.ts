import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, getAccessToken } from "@/lib/api";
import type { Job } from "@/types";

const TERMINAL = new Set(["COMPLETED", "FAILED"]);
const POLL_MS = 2000;

type StreamHandlers = {
  onUpdate?: (job: Job) => void;
  onDone?: () => void;
};

function applyJobUpdate(queryClient: ReturnType<typeof useQueryClient>, job: Job, handlers: StreamHandlers) {
  handlers.onUpdate?.(job);
  queryClient.setQueryData<Job>(["job", job.id], job);
  queryClient.setQueriesData<{ items: Job[]; next_cursor: string | null }>(
    { queryKey: ["jobs"] },
    (old) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.map((j) => (j.id === job.id ? { ...j, ...job } : j)),
      };
    }
  );
  queryClient.setQueriesData<Job[]>({ queryKey: ["recent-jobs"] }, (old) => {
    if (!old) return old;
    const idx = old.findIndex((j) => j.id === job.id);
    if (idx === -1) return [job, ...old];
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
      const key = `${job.status}:${job.output_url ?? ""}`;
      if (seen.get(job.id) === key) return;
      seen.set(job.id, key);
      applyJobUpdate(queryClient, job, handlersRef.current);
    };

    const allTerminal = (jobs: Job[]) =>
      jobs.length === activeIds.length && jobs.every((j) => TERMINAL.has(j.status));

    const pollJobs = async () => {
      if (cancelled) return;
      try {
        const results = await Promise.all(
          activeIds.map((id) => api.get<Job>(`/jobs/${id}`).then((r) => r.data))
        );
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
