import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Activity,
  AlertCircle,
  BarChart3,
  Database,
  KeyRound,
  SlidersHorizontal,
  TestTube2,
  Trash2,
  User as UserIcon,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { ProviderSettings } from "@/components/ProviderSettings";
import { PromptEditor } from "@/components/PromptEditor";
import { PromptSandbox } from "@/components/admin/PromptSandbox";
import { PromptFragmentsAdmin } from "@/components/admin/PromptFragmentsAdmin";
import { apiErrorMessage } from "@/lib/apiError";
import { StylePresetsAdmin } from "@/components/admin/StylePresetsAdmin";
import { UsageMonitor } from "@/components/admin/UsageMonitor";
import { UserManagement } from "@/components/admin/UserManagement";
import { api } from "@/lib/api";
import type { AdminMetrics, ConfigOptions, RateEntry } from "@/types";
import { label } from "@/types";

const TABS = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "monitoring", label: "Monitoring", icon: Activity },
  { id: "providers", label: "Providers", icon: KeyRound },
  { id: "prompts", label: "Prompts", icon: SlidersHorizontal },
  { id: "test", label: "Prompt Test", icon: TestTube2 },
  { id: "rates", label: "Rates", icon: Database },
  { id: "quality", label: "Quality", icon: AlertCircle },
  { id: "users", label: "Users", icon: UserIcon },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function AdminPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<TabId>("overview");
  const [rateDraft, setRateDraft] = useState({
    rate_type: "GOLD",
    metal_type: "24k Gold",
    diamond_shape: "",
    value: "",
    currency: "PKR",
    city: "",
  });

  const {
    data: metrics,
    isLoading: metricsLoading,
    isError: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ["admin", "metrics"],
    queryFn: async () => (await api.get<AdminMetrics>("/admin/metrics")).data,
  });

  const { data: options } = useQuery({
    queryKey: ["config", "options"],
    queryFn: async () => (await api.get<ConfigOptions>("/config/options")).data,
  });

  const { data: rates = [] } = useQuery({
    queryKey: ["rates"],
    queryFn: async () => (await api.get<RateEntry[]>("/rates")).data,
  });

  const { data: diagnostics, refetch: runDiagnostics, isFetching: diagnosticsLoading } = useQuery({
    queryKey: ["diagnostics"],
    queryFn: async () => (await api.get("/providers/health")).data,
    enabled: false,
  });

  const createRateMutation = useMutation({
    mutationFn: async () => {
      const numValue = parseFloat(String(rateDraft.value).replace(/,/g, ""));
      if (isNaN(numValue) || numValue <= 0) throw new Error("Invalid value");
      await api.post("/rates", { ...rateDraft, value: numValue });
    },
    onSuccess: () => {
      setRateDraft((d) => ({ ...d, value: "" }));
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      toast.success("Rate saved");
    },
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Failed to save rate")),
  });

  const deleteRateMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/rates/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rates"] });
      toast.success("Rate deleted");
    },
    onError: (err: Error) => toast.error(apiErrorMessage(err, "Failed to delete rate")),
  });

  return (
    <AppLayout subtitle="Admin Dashboard">
      <main className="mx-auto max-w-[1400px] w-full px-4 lg:px-8 py-6 flex-1">
        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-6 items-start">
          <aside className="space-y-1 lg:sticky lg:top-20">
            {TABS.map((item) => {
              const Icon = item.icon;
              const active = tab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTab(item.id)}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                    active
                      ? "bg-blue-600 text-white font-semibold shadow-sm"
                      : "text-slate-600 hover:bg-slate-100 font-medium"
                  }`}
                >
                  <Icon className="size-4 shrink-0" />
                  {item.label}
                </button>
              );
            })}
          </aside>

          <section className="min-w-0 space-y-6">
            {tab === "overview" && (
              <div className="space-y-6 animate-fadeIn">
                {metricsError && (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 flex items-center justify-between gap-3">
                    <span>Could not load admin metrics. Do not treat zeros as real data.</span>
                    <button
                      type="button"
                      className="shrink-0 rounded-lg bg-rose-700 px-3 py-1.5 text-xs font-bold text-white"
                      onClick={() => void refetchMetrics()}
                    >
                      Retry
                    </button>
                  </div>
                )}
                <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
                  {metricsLoading
                    ? Array.from({ length: 6 }).map((_, i) => (
                        <div
                          key={i}
                          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm animate-pulse"
                        >
                          <div className="h-3 w-16 rounded bg-slate-200" />
                          <div className="mt-3 h-7 w-12 rounded bg-slate-200" />
                        </div>
                      ))
                    : metricsError
                      ? null
                    : [
                        ["Total Jobs", metrics?.jobs ?? 0],
                        ["Completed", metrics?.completed ?? 0],
                        ["Failed", metrics?.failed ?? 0],
                        ["Assets", metrics?.assets ?? 0],
                        ["Batches", metrics?.batches ?? 0],
                        ["Favorites", metrics?.favorites ?? 0],
                      ].map(([name, value]) => (
                        <div key={name as string} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{name as string}</p>
                          <p className="text-2xl font-bold text-slate-800 mt-1">{value as number}</p>
                        </div>
                      ))}
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <p className="text-sm font-semibold text-slate-700">Success Rate</p>
                    <p className="text-lg font-bold">
                      {metricsLoading ? "—" : `${(metrics?.success_rate ?? 0).toFixed(1)}%`}
                    </p>
                  </div>
                  <div className="h-3 rounded-full bg-jewel-muted overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: metricsLoading ? "0%" : `${metrics?.success_rate ?? 0}%`,
                        backgroundColor: "var(--jewel-accent)",
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {tab === "monitoring" && <UsageMonitor />}

            {tab === "providers" && <ProviderSettings />}

            {tab === "prompts" && (
              <div className="space-y-6">
                <PromptEditor
                  workflows={options?.workflows ?? []}
                  jewelryTypes={options?.jewelryTypes ?? ["Ring"]}
                />
                <StylePresetsAdmin workflows={options?.workflows ?? []} />
                <PromptFragmentsAdmin />
              </div>
            )}

            {tab === "test" && <PromptSandbox options={options} />}

            {tab === "rates" && (
              <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-6 animate-fadeIn">
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6 space-y-3">
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Add Rate</h2>
                  <select
                    value={rateDraft.rate_type}
                    onChange={(e) => setRateDraft({ ...rateDraft, rate_type: e.target.value })}
                    className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs font-semibold"
                  >
                    <option value="GOLD">Gold</option>
                    <option value="SILVER">Silver</option>
                    <option value="DIAMOND">Diamond</option>
                  </select>
                  <input
                    placeholder="Metal type"
                    value={rateDraft.metal_type}
                    onChange={(e) => setRateDraft({ ...rateDraft, metal_type: e.target.value })}
                    className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
                  />
                  <input
                    placeholder="Value"
                    value={rateDraft.value}
                    onChange={(e) => setRateDraft({ ...rateDraft, value: e.target.value })}
                    className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
                  />
                  <input
                    placeholder="City"
                    value={rateDraft.city}
                    onChange={(e) => setRateDraft({ ...rateDraft, city: e.target.value })}
                    className="h-10 w-full rounded-lg border border-slate-200 px-3 text-xs"
                  />
                  <button
                    type="button"
                    onClick={() => createRateMutation.mutate()}
                    disabled={createRateMutation.isPending}
                    className="h-10 w-full rounded-lg bg-blue-600 text-xs font-bold text-white"
                  >
                    Save Rate
                  </button>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6 space-y-3 max-h-[600px] overflow-y-auto">
                  {rates.map((rate) => (
                    <div
                      key={rate.id}
                      className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/50 p-4"
                    >
                      <div>
                        <p className="font-bold text-xs text-slate-800">{rate.rate_type}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          {[rate.metal_type, rate.city].filter(Boolean).join(" • ")}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-blue-700 text-sm">
                          {rate.currency} {rate.value.toLocaleString()}
                        </span>
                        <button
                          type="button"
                          onClick={() => deleteRateMutation.mutate(rate.id)}
                          className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg"
                        >
                          <Trash2 className="size-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === "quality" && (
              <div className="space-y-6 animate-fadeIn">
                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Provider Health</h2>
                    <button
                      type="button"
                      onClick={() => runDiagnostics()}
                      disabled={diagnosticsLoading}
                      className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 px-3 text-xs font-bold"
                    >
                      <Activity className="size-3.5 text-blue-600" />
                      {diagnosticsLoading ? "Running…" : "Run Check"}
                    </button>
                  </div>
                  {diagnostics && (
                    <pre className="max-h-[300px] overflow-auto rounded-xl bg-slate-950 p-4 text-[10px] font-mono text-slate-200 whitespace-pre-wrap">
                      {JSON.stringify(diagnostics, null, 2)}
                    </pre>
                  )}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white shadow-sm p-6 space-y-3">
                  <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Recent Failures</h2>
                  {metrics?.recent_failures?.length ? (
                    metrics.recent_failures.map((f) => (
                      <div
                        key={f.id}
                        className="rounded-xl border border-rose-100 bg-rose-50/40 p-4 border-l-4 border-l-rose-500"
                      >
                        <p className="font-bold text-xs text-rose-800">{label(f.workflow)}</p>
                        <p className="text-[10px] text-rose-600 mt-1 font-mono">ID: {f.id}</p>
                        <p className="text-xs text-rose-700 mt-2">{f.error}</p>
                        <Link
                          to={`/?jobId=${f.id}`}
                          className="inline-block mt-2 text-xs font-bold text-blue-600 hover:underline"
                        >
                          Open in Studio →
                        </Link>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-500 py-6 text-center">No recent failures.</p>
                  )}
                </div>
              </div>
            )}

            {tab === "users" && <UserManagement />}
          </section>
        </div>
      </main>
    </AppLayout>
  );
}
