import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, RefreshCw } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { FacetMark } from "@/components/ui/FacetMark";
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
  const navigate = useNavigate();
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
          <Activity className="size-4 text-[var(--jewel-accent)]" />
          <div>
            <h2 className="ui-card-title">Usage monitor</h2>
            <p className="text-[11px] text-[var(--jewel-ink-muted)]">
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
            disabled={isFetching}
            aria-busy={isFetching}
            className="ui-btn-secondary h-9"
          >
            {isFetching ? (
              <FacetMark variant="spin" size={14} className="text-[var(--jewel-accent)]" />
            ) : (
              <RefreshCw className="size-3.5" />
            )}
            {isFetching ? "Refreshing…" : "Refresh"}
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
          <div className="ui-stats-strip">
            {[
              ["Jobs (all)", summary.total_jobs],
              ["Completed", summary.completed],
              ["Failed", summary.failed],
              ["In flight", summary.pending + summary.processing],
              ["Est. cost (window)", money(summary.estimated_cost_usd_window)],
              ["Est. cost (all)", money(summary.estimated_cost_usd_all_time)],
            ].map(([name, value]) => (
              <div key={String(name)} className="ui-stats-strip__cell">
                <p className="text-[11px] text-[var(--jewel-ink-muted)]">{name}</p>
                <p className="mt-1 text-lg font-semibold font-mono-data text-jewel-ink">{value}</p>
              </div>
            ))}
          </div>

          {data.live_jobs.length > 0 && (
            <div className="rounded-2xl border border-blue-100 bg-blue-50/40 p-4">
              <p className="text-xs font-semibold text-blue-800 mb-2">Live queue</p>
              <div className="space-y-1.5">
                {data.live_jobs.map((j) => (
                  <Link
                    key={j.id}
                    to={`/?jobId=${j.id}`}
                    className="ui-row--interactive flex flex-wrap items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-slate-700 -mx-1"
                  >
                    <span className={`rounded border px-1.5 py-0.5 font-semibold ${statusClass(j.status)}`}>{j.status}</span>
                    <span className="font-medium">{j.workflow}</span>
                    <span className="text-slate-500">{shortModel(j.model)}</span>
                    <span className="text-slate-400">{j.user_email || "—"}</span>
                    <span className="font-mono text-[10px] text-slate-400">{j.id.slice(0, 8)}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="ui-card p-5">
            <p className="ui-card-title mb-3">Daily volume ({days}d)</p>
            {data.by_day.length === 0 ? (
              <EmptyState
                compact
                title="No jobs in this window"
                description="Volume will appear once generations run."
              />
            ) : data.by_day.filter((d) => d.total > 0).length < 5 ? (
              <EmptyState
                compact
                title="Not enough volume yet"
                description="Need a few more active days before the chart is useful. Counts still show in the tables below."
              />
            ) : (
              <div className="space-y-2">
                <div className="flex items-end gap-1 h-28 relative">
                  <div
                    className="absolute inset-0 flex flex-col justify-between pointer-events-none py-1"
                    aria-hidden
                  >
                    {[0, 1, 2, 3].map((i) => (
                      <div key={i} style={{ borderTop: "1px solid var(--jewel-hairline)" }} />
                    ))}
                  </div>
                  {data.by_day.map((d) => {
                    const px = Math.max(4, Math.round((d.total / maxDay) * 96));
                    return (
                      <div
                        key={d.date}
                        className="relative z-[1] flex-1 min-w-0 flex flex-col justify-end items-center h-full"
                        title={`${d.date}: ${d.total} jobs, ${money(d.estimated_cost_usd)}`}
                      >
                        <div
                          className="w-full rounded-t"
                          style={{
                            height: `${px}px`,
                            background:
                              "linear-gradient(180deg, color-mix(in srgb, var(--jewel-accent) 50%, white) 0%, var(--jewel-accent) 24%, var(--jewel-accent) 100%)",
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
                <div className="flex gap-1">
                  {data.by_day.map((d) => (
                    <span
                      key={`lbl-${d.date}`}
                      className="flex-1 min-w-0 text-[9px] text-[var(--jewel-ink-faint)] truncate text-center font-mono-data"
                    >
                      {d.date.slice(5)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
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
                {data.by_model.map((m, i) => (
                  <tr
                    key={m.model}
                    className={`border-t border-slate-100 text-xs ${i % 2 === 1 ? "bg-[var(--jewel-surface-muted)]" : ""}`}
                  >
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
                {data.by_workflow.map((w, i) => (
                  <tr
                    key={w.workflow}
                    className={`border-t border-slate-100 text-xs ${i % 2 === 1 ? "bg-[var(--jewel-surface-muted)]" : ""}`}
                  >
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
                {data.by_user.map((u, i) => (
                  <tr
                    key={u.user_id || u.email}
                    className={`border-t border-slate-100 text-xs ${i % 2 === 1 ? "bg-[var(--jewel-surface-muted)]" : ""}`}
                  >
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
                {data.recent_jobs.map((j, i) => (
                  <tr
                    key={j.id}
                    className={`ui-row--interactive border-t border-slate-100 align-top ${i % 2 === 1 ? "bg-[var(--jewel-surface-muted)]" : ""}`}
                    tabIndex={0}
                    role="link"
                    onClick={() => navigate(`/?jobId=${j.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        navigate(`/?jobId=${j.id}`);
                      }
                    }}
                  >
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
                    <td
                      className="py-2 text-rose-600 max-w-[220px]"
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()}
                    >
                      {j.error_message ? (
                        <details>
                          <summary className="cursor-pointer truncate max-w-[220px] list-none">
                            <span className="underline-offset-2 hover:underline">
                              {j.error_message.slice(0, 80)}
                              {j.error_message.length > 80 ? "…" : ""}
                            </span>
                          </summary>
                          <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap text-[10px] font-mono text-rose-700">
                            {j.error_message}
                          </pre>
                        </details>
                      ) : (
                        "—"
                      )}
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
    <div className="ui-card p-5 overflow-x-auto">
      <p className="ui-card-title mb-3">{title}</p>
      <table className="w-full">{children}</table>
    </div>
  );
}
