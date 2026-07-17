import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "@/components/AppLayout";
import { api } from "@/lib/api";
import type { RateEntry } from "@/types";

export function RatesPage() {
  const {
    data: rates = [],
    isLoading: ratesLoading,
    isError: ratesError,
    refetch: refetchRates,
  } = useQuery({
    queryKey: ["rates"],
    queryFn: async () => (await api.get<RateEntry[]>("/rates")).data,
    retry: 2,
  });

  const {
    data: liveRates,
    isLoading: liveLoading,
    isError: liveError,
    refetch: refetchLive,
  } = useQuery({
    queryKey: ["rates", "live"],
    queryFn: async () =>
      (await api.get<{ gold_pkr_per_gram?: number; silver_pkr_per_gram?: number }>("/rates/live")).data,
    retry: 2,
  });

  return (
    <AppLayout subtitle="Market Rates">
      <main className="mx-auto max-w-4xl w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <header>
          <h2 className="text-2xl font-semibold text-slate-900">Rate Tools</h2>
          <p className="mt-1 text-sm text-slate-500">
            Live spot prices and your store’s local rate sheet.
          </p>
        </header>

        <section className="ui-card p-5 sm:p-6">
          <h3 className="ui-label mb-3">Live Spot Rates</h3>
          {liveLoading ? (
            <p className="text-sm text-slate-500">Loading live rates…</p>
          ) : liveError ? (
            <div className="space-y-2">
              <p className="text-sm text-slate-500">Could not load live rates.</p>
              <button type="button" className="ui-btn-secondary" onClick={() => void refetchLive()}>
                Retry
              </button>
            </div>
          ) : liveRates?.gold_pkr_per_gram != null ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-medium text-slate-500">Gold (PKR/g)</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {liveRates.gold_pkr_per_gram.toLocaleString()}
                </p>
              </div>
              <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-4">
                <p className="text-xs font-medium text-slate-500">Silver (PKR/g)</p>
                <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">
                  {liveRates.silver_pkr_per_gram?.toLocaleString()}
                </p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Live feed unavailable right now.</p>
          )}
        </section>

        <section className="ui-card p-5 sm:p-6">
          <h3 className="ui-label mb-3">Local Rates</h3>
          {ratesLoading ? (
            <p className="text-sm text-slate-500">Loading local rates…</p>
          ) : ratesError ? (
            <div className="space-y-2">
              <p className="text-sm text-slate-500">Could not load local rates.</p>
              <button type="button" className="ui-btn-secondary" onClick={() => void refetchRates()}>
                Retry
              </button>
            </div>
          ) : rates.length ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {rates.map((r) => (
                <div key={r.id} className="rounded-xl border border-slate-100 p-3.5">
                  <p className="text-sm font-semibold text-slate-800">{r.rate_type}</p>
                  <p className="mt-1 text-sm font-semibold tabular-nums text-blue-700">
                    {r.currency} {r.value.toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Add rates in Admin → Rates.</p>
          )}
        </section>
      </main>
    </AppLayout>
  );
}
