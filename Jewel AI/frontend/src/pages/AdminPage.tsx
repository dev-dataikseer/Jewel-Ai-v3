import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BarChart3,
  KeyRound,
  SlidersHorizontal,
  User as UserIcon,
} from "lucide-react";
import { AppLayout } from "@/components/AppLayout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { FacetMark } from "@/components/ui/FacetMark";
import { ProviderSettings } from "@/components/ProviderSettings";
import { PromptEditor } from "@/components/PromptEditor";
import { PromptFragmentsAdmin } from "@/components/admin/PromptFragmentsAdmin";
import { PromptToolsAdmin } from "@/components/admin/PromptToolsAdmin";
import { StylePresetsAdmin } from "@/components/admin/StylePresetsAdmin";
import { UsageMonitor } from "@/components/admin/UsageMonitor";
import { UserManagement } from "@/components/admin/UserManagement";
import { MfaAdminPanel } from "@/components/admin/MfaAdminPanel";
import { api } from "@/lib/api";
import type { AdminMetrics, ConfigOptions } from "@/types";

const TABS = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "monitoring", label: "Monitoring", icon: Activity },
  { id: "providers", label: "Providers", icon: KeyRound },
  { id: "prompts", label: "Prompts", icon: SlidersHorizontal },
  { id: "users", label: "Users", icon: UserIcon },
] as const;

type TabId = (typeof TABS)[number]["id"];

const PROMPT_SUBTABS = [
  { id: "workflows", label: "Workflow prompts" },
  { id: "fragments", label: "Shared fragments" },
  { id: "presets", label: "Style presets" },
  { id: "tools", label: "Tools" },
] as const;

type PromptSubtab = (typeof PROMPT_SUBTABS)[number]["id"];

function AdminPromptsSection({
  workflows,
  jewelryTypes,
}: {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
}) {
  const [sub, setSub] = useState<PromptSubtab>("workflows");
  return (
    <div className="flex flex-col gap-4 animate-fadeIn">
      <div className="flex flex-wrap gap-1 rounded-xl border border-[var(--jewel-border)] bg-white p-1">
        {PROMPT_SUBTABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setSub(item.id)}
            className={`rounded-lg px-3 py-2 text-[12px] font-semibold transition-colors ${
              sub === item.id
                ? "bg-[var(--jewel-accent-soft)] text-[var(--jewel-accent)]"
                : "text-jewel-ink-muted hover:bg-[var(--jewel-surface-muted)]"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {sub === "workflows" && (
        <PromptEditor workflows={workflows} jewelryTypes={jewelryTypes} />
      )}
      {sub === "fragments" && <PromptFragmentsAdmin />}
      {sub === "presets" && <StylePresetsAdmin workflows={workflows} />}
      {sub === "tools" && <PromptToolsAdmin />}
    </div>
  );
}
export function AdminPage() {
  const [tab, setTab] = useState<TabId>("overview");

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

  return (
    <AppLayout subtitle="AI Creative Suite">
      <main className="mx-auto max-w-[1400px] w-full px-4 lg:px-8 py-6 bg-[var(--jewel-bg)] min-h-0 flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-6 items-start">
          <aside className="ui-card p-2 space-y-0.5 lg:sticky lg:top-20">
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
                      ? "ui-nav-active-tab"
                      : "text-jewel-ink-muted hover:bg-jewel-muted font-medium"
                  }`}
                >
                  <Icon className="size-4 shrink-0" />
                  {item.label}
                </button>
              );
            })}
          </aside>

          <section className="ui-admin-shell min-w-0">
            <ErrorBoundary key={tab}>
            {tab === "overview" && (
              <div className="animate-fadeIn space-y-6">
                <div className="flex items-center justify-between gap-3">
                  <h1 className="text-lg font-semibold text-jewel-ink">Overview</h1>
                  <button
                    type="button"
                    onClick={() => void refetchMetrics()}
                    className="ui-btn-secondary h-9 text-xs"
                    disabled={metricsLoading}
                  >
                    <FacetMark
                      variant={metricsLoading ? "spin" : "check"}
                      size={14}
                      className="text-[var(--jewel-accent)]"
                    />
                    Refresh
                  </button>
                </div>
                {metricsError ? (
                  <p className="text-sm text-rose-600">Could not load metrics.</p>
                ) : (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
                      {[
                        { label: "Jobs", value: metrics?.jobs },
                        { label: "Completed", value: metrics?.completed },
                        { label: "Failed", value: metrics?.failed },
                        { label: "Assets", value: metrics?.assets },
                        { label: "Batches", value: metrics?.batches },
                        { label: "Favorites", value: metrics?.favorites },
                      ].map((card) => (
                        <div key={card.label} className="ui-card p-4">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-jewel-ink-muted">
                            {card.label}
                          </p>
                          <p className="mt-1 text-2xl font-semibold tabular-nums text-jewel-ink">
                            {metricsLoading ? "…" : (card.value ?? "—")}
                          </p>
                        </div>
                      ))}
                    </div>
                    {!metricsLoading ? (
                      <div className="ui-card p-5">
                        <div className="flex items-center justify-between mb-2">
                          <p className="text-sm font-semibold text-jewel-ink">Success rate</p>
                          <p className="text-lg font-semibold tabular-nums text-jewel-ink">
                            {(metrics?.success_rate ?? 0).toFixed(1)}%
                          </p>
                        </div>
                        <div className="h-2.5 rounded-full bg-[var(--jewel-surface-muted)] overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, Math.max(0, metrics?.success_rate ?? 0))}%`,
                              backgroundColor: "var(--jewel-accent)",
                            }}
                          />
                        </div>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            )}

            {tab === "monitoring" && <UsageMonitor />}

            {tab === "providers" && <ProviderSettings />}

            {tab === "prompts" && (
              <AdminPromptsSection
                workflows={options?.workflows ?? []}
                jewelryTypes={options?.jewelryTypes ?? ["Ring"]}
              />
            )}

            {tab === "users" && (
              <div className="flex flex-col gap-6">
                <MfaAdminPanel />
                <UserManagement />
              </div>
            )}
            </ErrorBoundary>
          </section>
        </div>
      </main>
    </AppLayout>
  );
}
