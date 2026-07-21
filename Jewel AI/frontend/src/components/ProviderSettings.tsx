import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Activity, Info, Save, Wallet } from "lucide-react";
import { FacetMark } from "@/components/ui/FacetMark";
import { StatusDot } from "@/components/ui/StatusDot";
import { api } from "@/lib/api";
import type { FalCreditsResponse } from "@/components/FalCreditsWidget";
import type { ModelDefinition, Provider } from "@/types";

export function ProviderSettings() {
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [adminApiKey, setAdminApiKey] = useState("");
  const [modelEndpoint, setModelEndpoint] = useState("fal-ai/flux-pro/kontext");

  const { data: providers = [], isLoading } = useQuery({
    queryKey: ["providers"],
    queryFn: async () => (await api.get<Provider[]>("/providers")).data,
  });

  const { data: models = [] } = useQuery({
    queryKey: ["models", "fal-provider-settings"],
    queryFn: async () => (await api.get<ModelDefinition[]>("/models/admin")).data,
  });

  const fal = providers.find((p) => p.name === "FAL");

  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.patch("/providers/FAL", {
        api_key: apiKey || undefined,
        admin_api_key: adminApiKey || undefined,
        model_name: modelEndpoint,
      });
    },
    onSuccess: () => {
      setApiKey("");
      setAdminApiKey("");
      queryClient.invalidateQueries({ queryKey: ["providers"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "fal-credits"] });
      toast.success("fal.ai settings saved");
    },
    onError: () => toast.error("Failed to save fal.ai settings"),
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<{ healthy: boolean; message: string }>("/providers/FAL/test");
      return res.data;
    },
    onSuccess: (data) => {
      if (data.healthy) toast.success(data.message || "fal.ai connection OK");
      else toast.error(data.message || "fal.ai connection failed");
    },
    onError: () => toast.error("fal.ai provider test failed"),
  });

  const testBillingMutation = useMutation({
    mutationFn: async () =>
      (await api.post<FalCreditsResponse>("/billing/fal-credits/refresh")).data,
    onSuccess: (data) => {
      queryClient.setQueryData(["billing", "fal-credits"], data);
      if (data.available && data.current_balance != null) {
        toast.success(
          `Billing OK — ${data.currency} ${data.current_balance.toFixed(2)}` +
            (data.username ? ` (${data.username})` : "")
        );
      } else {
        toast.error(data.error || "Billing credits unavailable — check Admin API key");
      }
    },
    onError: () => toast.error("Billing refresh failed"),
  });

  if (isLoading) {
    return <p className="text-sm text-slate-500">Loading provider...</p>;
  }

  return (
    <div className="ui-panel-hero overflow-hidden w-full">
      <div
        className="border-b border-[var(--jewel-border)] px-6 py-4"
        style={{ backgroundColor: "var(--jewel-surface-muted)" }}
      >
        <h2 className="text-sm font-semibold text-slate-800">fal.ai provider settings</h2>
        <p className="mt-1 text-xs text-slate-500">
          Paste an admin-scoped fal key to show live credits in the header.
          <span
            className="ml-1 inline-flex align-middle text-slate-400 cursor-help"
            title="Admin keys come from fal dashboard → Keys → Admin. Billing uses GET /account/billing?expand=credits. You can also set FAL_ADMIN_KEY in backend/.env. API-scoped keys return 403 on billing."
          >
            <Info className="size-3.5" aria-label="More about admin keys" />
          </span>
        </p>
      </div>

      <div className="ui-admin-cols ui-admin-cols-60 gap-0 lg:divide-x divide-[var(--jewel-border)]">
        <div className="p-6 space-y-5">
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-600">
              Default fal.ai model
            </label>
            <select
              value={modelEndpoint}
              onChange={(e) => setModelEndpoint(e.target.value)}
              className="ui-input text-xs font-semibold"
            >
              {models.map((m) => (
                <option key={m.endpoint_id} value={m.endpoint_id}>
                  {m.display_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-600">
              FAL_KEY (generation)
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={fal?.has_api_key ? "Saved — enter to replace" : "Enter fal.ai API key"}
              className="ui-input text-xs font-semibold"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-600">
              FAL Admin API key (billing / credits)
            </label>
            <input
              type="password"
              value={adminApiKey}
              onChange={(e) => setAdminApiKey(e.target.value)}
              placeholder={
                fal?.has_admin_api_key
                  ? "Saved — enter to replace Admin-scoped key"
                  : "Paste Admin API key (Authorization: Key …)"
              }
              className="ui-input text-xs font-semibold"
            />
          </div>
          <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
              aria-busy={saveMutation.isPending}
              className="ui-btn-primary h-10 px-5 text-xs"
            >
              {saveMutation.isPending ? (
                <FacetMark variant="spin" size={14} className="text-white" />
              ) : (
                <Save className="size-4" />
              )}
              {saveMutation.isPending ? "Saving…" : "Save Configuration"}
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4" style={{ backgroundColor: "var(--jewel-surface-muted)" }}>
          <h3 className="text-sm font-semibold text-slate-800">Live health & credits</h3>
          <div className="ui-card-muted p-4 space-y-2">
            <p className="text-xs text-slate-500">Connection</p>
            <p className="text-sm font-semibold text-slate-800">
              {fal ? (
                <span className="inline-flex items-center gap-2">
                  <StatusDot
                    tone={
                      String(fal.health_status || "").toLowerCase().includes("health") ||
                      String(fal.health_status || "").toLowerCase() === "ok"
                        ? "ok"
                        : "warn"
                    }
                  />
                  <span>
                    {fal.model_name} · {fal.health_status}
                  </span>
                </span>
              ) : (
                "No fal provider row yet"
              )}
            </p>
            <p className="text-[11px] text-slate-500">
              API key: {fal?.has_api_key ? "saved" : "missing"} · Admin key:{" "}
              {fal?.has_admin_api_key ? "saved" : "missing"}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => testMutation.mutate()}
              disabled={testMutation.isPending}
              aria-busy={testMutation.isPending}
              className="ui-btn-secondary h-10 px-4"
            >
              {testMutation.isPending ? (
                <FacetMark variant="spin" size={14} className="text-[var(--jewel-accent)]" />
              ) : (
                <Activity className="size-4 text-blue-600" />
              )}
              {testMutation.isPending ? "Testing…" : "Test fal.ai"}
            </button>
            <button
              type="button"
              onClick={() => testBillingMutation.mutate()}
              disabled={testBillingMutation.isPending}
              aria-busy={testBillingMutation.isPending}
              className="ui-btn-secondary h-10 px-4"
            >
              {testBillingMutation.isPending ? (
                <FacetMark variant="spin" size={14} className="text-emerald-600" />
              ) : (
                <Wallet className="size-4 text-emerald-600" />
              )}
              {testBillingMutation.isPending ? "Checking…" : "Test billing / credits"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
