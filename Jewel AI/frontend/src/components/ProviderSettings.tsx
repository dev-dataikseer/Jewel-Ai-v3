import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Activity, Save, Wallet } from "lucide-react";
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
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">fal.ai Provider Settings</h2>
        <p className="text-xs text-slate-500 mt-1">
          Generation uses an API-scoped key. Credits in the header require an{" "}
          <span className="font-semibold text-slate-700">Admin-scoped</span> key (fal dashboard → Keys → Admin)
          for <code className="text-[10px]">GET /account/billing?expand=credits</code>.
        </p>
      </div>
      <div className="p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Default fal.ai Model
            </label>
            <select
              value={modelEndpoint}
              onChange={(e) => setModelEndpoint(e.target.value)}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-500"
            >
              {models.map((m) => (
                <option key={m.endpoint_id} value={m.endpoint_id}>
                  {m.display_name}
                </option>
              ))}
            </select>
            {fal && (
              <p className="mt-2 text-[11px] text-slate-400">
                Current: {fal.model_name} · {fal.health_status}
              </p>
            )}
          </div>
          <div>
            <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
              FAL_KEY (generation)
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={fal?.has_api_key ? "Saved — enter to replace" : "Enter fal.ai API key"}
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="md:col-span-2">
            <label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
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
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-800 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1.5 text-[11px] text-slate-400">
              Required for header Credits. API-scope keys return 403 on billing. You can also set{" "}
              <code className="text-[10px]">FAL_ADMIN_KEY</code> in backend/.env.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-100">
          <button
            type="button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-5 text-xs font-bold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <Save className="size-4" />
            {saveMutation.isPending ? "Saving..." : "Save Configuration"}
          </button>
          <button
            type="button"
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            <Activity className="size-4 text-blue-600" />
            {testMutation.isPending ? "Testing..." : "Test fal.ai"}
          </button>
          <button
            type="button"
            onClick={() => testBillingMutation.mutate()}
            disabled={testBillingMutation.isPending}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-5 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            <Wallet className="size-4 text-emerald-600" />
            {testBillingMutation.isPending ? "Checking…" : "Test billing / credits"}
          </button>
        </div>
      </div>
    </div>
  );
}
