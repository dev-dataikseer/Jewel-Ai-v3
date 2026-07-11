import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Loader2, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import type { UsageAnalytics } from "@/types";

function money(n: number | null | undefined) {
  return `$${(n ?? 0).toFixed(4)}`;
}

function shortModel(model?: string | null) {
  if (!model) return "—";
  const parts = model.split("/");
  return parts[parts.length - 1] || model;
}

function statusClass(status: string) {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-50 text-emerald-700 border-emerald-100";
    case "FAILED":
      return "bg-rose-50 text-rose-700 border-rose-100";
    case "PROCESSING":
      return "bg-blue-50 text-blue-700 border-blue-100";
    case "PENDING":
      return "bg-amber-50 text-amber-800 border-amber-100";
    default:
      return "bg-slate-50 text-slate-600 border-slate-100";
  }
}

export function UsageMonitor() {
  const [days, setDays] = useState(30);
  const { data, isLoading, isFetching, isError, error, refetch } = useQuery({
    queryKey: ["admin", "usage", days],
    queryFn: async () => (await api.get<UsageAnalytics>("/admin/usage", { params: { days, limit: 80 } })).data,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const maxDay = useMemo(() => Math.max(1, ...(data?.by_day.map((d) => d.total) ?? [1])), [data]);
  const summary = data?.summary;

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-blue-600" />
          <div>
            <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Usage Monitor</h2>
            <p className="text-[11px] text-slate-500">
              Job states, models, and estimated catalog cost — fal.ai remains the billing source of truth.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="h-9 rounded-lg border border-slate-200 px-2 text-xs font-semibold"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-700"
          >
            {isFetching ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Refresh
          </button>
        </div>
      </div>

      {isError ? (
        <p className="text-sm text-rose-600">
          Failed to load usage{(error as { friendlyMessage?: string })?.friendlyMessage ? `: ${(error as { friendlyMessage?: string }).friendlyMessage}` : "."}
        </p>
      ) : isLoading || !summary ? (
        <p className="text-sm text-slate-500">Loading usage…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
            {[
              ["Jobs (all)", summary.total_jobs],
              ["Completed", summary.completed],
              ["Failed", summary.failed],
              ["In flight", summary.pending + summary.processing],
              ["Est. cost (window)", money(summary.estimated_cost_usd_window)],
              ["Est. cost (all)", money(summary.estimated_cost_usd_all_time)],
            ].map(([name, value]) => (
              <div key={String(name)} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{name}</p>
                <p className="text-xl font-bold text-slate-800 mt-1">{value}</p>
              </div>
            ))}
          </div>

          {data.live_jobs.length > 0 && (
            <div className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4">
              <p className="text-xs font-bold uppercase tracking-wide text-blue-800 mb-2">Live queue</p>
              <div className="space-y-1.5">
                {data.live_jobs.map((j) => (
                  <div key={j.id} className="flex flex-wrap items-center gap-2 text-xs text-slate-700">
                    <span className={`rounded border px-1.5 py-0.5 font-semibold ${statusClass(j.status)}`}>{j.status}</span>
                    <span className="font-medium">{j.workflow}</span>
                    <span className="text-slate-500">{shortModel(j.model)}</span>
                    <span className="text-slate-400">{j.user_email || "—"}</span>
                    <span className="font-mono text-[10px] text-slate-400">{j.id.slice(0, 8)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-slate-700 mb-3">Daily volume ({days}d)</p>
            {data.by_day.length === 0 ? (
              <p className="text-xs text-slate-500">No jobs in this window.</p>
            ) : (
              <div className="flex items-end gap-1 h-28">
                {data.by_day.map((d) => {
                  const px = Math.max(4, Math.round((d.total / maxDay) * 96));
                  return (
                  <div key={d.date} className="flex-1 min-w-0 flex flex-col justify-end items-center gap-1 h-full" title={`${d.date}: ${d.total} jobs, ${money(d.estimated_cost_usd)}`}>
                    <div
                      className="w-full rounded-t bg-blue-500/80"
                      style={{ height: `${px}px` }}
                    />
                    <span className="text-[9px] text-slate-400 truncate w-full text-center">{d.date.slice(5)}</span>
                  </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <TableCard title="By model">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="pb-2 font-bold">Model</th>
                  <th className="pb-2 font-bold">Jobs</th>
                  <th className="pb-2 font-bold">OK</th>
                  <th className="pb-2 font-bold">Fail</th>
                  <th className="pb-2 font-bold">Est. $</th>
                </tr>
              </thead>
              <tbody>
                {data.by_model.map((m) => (
                  <tr key={m.model} className="border-t border-slate-100 text-xs">
                    <td className="py-2 pr-2">
                      <p className="font-semibold text-slate-800 truncate max-w-[220px]" title={m.model}>
                        {shortModel(m.model)}
                      </p>
                      <p className="text-[10px] text-slate-400">{m.provider}</p>
                    </td>
                    <td className="py-2">{m.total}</td>
                    <td className="py-2 text-emerald-700">{m.completed}</td>
                    <td className="py-2 text-rose-600">{m.failed}</td>
                    <td className="py-2 font-mono">{money(m.estimated_cost_usd)}</td>
                  </tr>
                ))}
                {data.by_model.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-4 text-slate-500">
                      No model usage yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </TableCard>

            <TableCard title="By workflow">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="pb-2 font-bold">Workflow</th>
                  <th className="pb-2 font-bold">Jobs</th>
                  <th className="pb-2 font-bold">OK</th>
                  <th className="pb-2 font-bold">Fail</th>
                  <th className="pb-2 font-bold">Est. $</th>
                </tr>
              </thead>
              <tbody>
                {data.by_workflow.map((w) => (
                  <tr key={w.workflow} className="border-t border-slate-100 text-xs">
                    <td className="py-2 font-semibold text-slate-800">{w.workflow}</td>
                    <td className="py-2">{w.total}</td>
                    <td className="py-2 text-emerald-700">{w.completed}</td>
                    <td className="py-2 text-rose-600">{w.failed}</td>
                    <td className="py-2 font-mono">{money(w.estimated_cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </TableCard>

            <TableCard title="By user">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="pb-2 font-bold">User</th>
                  <th className="pb-2 font-bold">Jobs</th>
                  <th className="pb-2 font-bold">OK</th>
                  <th className="pb-2 font-bold">Fail</th>
                  <th className="pb-2 font-bold">Est. $</th>
                </tr>
              </thead>
              <tbody>
                {data.by_user.map((u) => (
                  <tr key={u.user_id || u.email} className="border-t border-slate-100 text-xs">
                    <td className="py-2 font-semibold text-slate-800 truncate max-w-[200px]">{u.email}</td>
                    <td className="py-2">{u.total}</td>
                    <td className="py-2 text-emerald-700">{u.completed}</td>
                    <td className="py-2 text-rose-600">{u.failed}</td>
                    <td className="py-2 font-mono">{money(u.estimated_cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </TableCard>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm overflow-x-auto">
            <p className="text-sm font-semibold text-slate-700 mb-3">Recent jobs</p>
            <table className="w-full min-w-[900px] text-xs">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="pb-2 font-bold">Status</th>
                  <th className="pb-2 font-bold">When</th>
                  <th className="pb-2 font-bold">User</th>
                  <th className="pb-2 font-bold">Workflow</th>
                  <th className="pb-2 font-bold">Model</th>
                  <th className="pb-2 font-bold">Est. $</th>
                  <th className="pb-2 font-bold">Duration</th>
                  <th className="pb-2 font-bold">Error</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_jobs.map((j) => (
                  <tr key={j.id} className="border-t border-slate-100 align-top">
                    <td className="py-2">
                      <span className={`rounded border px-1.5 py-0.5 font-semibold ${statusClass(j.status)}`}>{j.status}</span>
                    </td>
                    <td className="py-2 text-slate-500 whitespace-nowrap">
                      {j.created_at ? new Date(j.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2">{j.user_email || "—"}</td>
                    <td className="py-2 font-medium">{j.workflow}</td>
                    <td className="py-2" title={j.model || undefined}>
                      {shortModel(j.model)}
                    </td>
                    <td className="py-2 font-mono">{j.estimated_cost_usd != null ? money(j.estimated_cost_usd) : "—"}</td>
                    <td className="py-2 text-slate-500">
                      {j.duration_ms != null ? `${(j.duration_ms / 1000).toFixed(1)}s` : "—"}
                    </td>
                    <td className="py-2 text-rose-600 max-w-[220px] truncate" title={j.error_message || undefined}>
                      {j.error_message || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function TableCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm overflow-x-auto">
      <p className="text-sm font-semibold text-slate-700 mb-3">{title}</p>
      <table className="w-full">{children}</table>
    </div>
  );
}
