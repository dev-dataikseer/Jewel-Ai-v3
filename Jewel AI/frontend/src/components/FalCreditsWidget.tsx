import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCcw, Wallet } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

export type FalCreditsResponse = {
  available: boolean;
  current_balance: number | null;
  currency: string;
  username?: string | null;
  updated_at?: string | null;
  low_balance: boolean;
  low_threshold: number;
  stale: boolean;
  error?: string | null;
  error_type?: string | null;
};

function formatBalance(balance: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(balance);
  } catch {
    return `$${(balance ?? 0).toFixed(2)}`;
  }
}

function formatUpdatedAt(iso?: string | null) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return null;
    return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  } catch {
    return null;
  }
}

export function FalCreditsWidget() {
  const queryClient = useQueryClient();
  const { isAdmin } = useAuth();

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ["billing", "fal-credits"],
    queryFn: async () =>
      (await api.get<FalCreditsResponse>("/billing/fal-credits")).data,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
    retry: 1,
  });

  const refresh = useMutation({
    mutationFn: async () => {
      if (isAdmin) {
        return (await api.post<FalCreditsResponse>("/billing/fal-credits/refresh")).data;
      }
      const res = await refetch();
      return res.data as FalCreditsResponse;
    },
    onSuccess: (next) => {
      if (next) queryClient.setQueryData(["billing", "fal-credits"], next);
    },
  });

  const updated = formatUpdatedAt(data?.updated_at);
  const showLow = Boolean(data?.low_balance && data.available);
  const label =
    data?.available && data.current_balance != null
      ? formatBalance(data.current_balance, data.currency)
      : "Unavailable";

  const titleHint = data?.error
    ? `Last error: ${data.error}`
    : data?.username
      ? `fal.ai account: ${data.username}`
      : "fal.ai credit balance (requires FAL_ADMIN_KEY with Admin scope)";

  return (
    <div
      className={`inline-flex h-8 max-w-[260px] items-center gap-1.5 rounded-lg border px-2 text-[12px] font-medium ${
        showLow
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-slate-200 bg-slate-50 text-slate-700"
      }`}
      title={titleHint}
    >
      {showLow ? (
        <AlertTriangle className="size-3.5 shrink-0 text-amber-600" aria-hidden />
      ) : (
        <Wallet className="size-3.5 shrink-0 text-slate-500" aria-hidden />
      )}
      <div className="min-w-0 leading-tight">
        <p className="truncate tabular-nums">
          {isLoading && !data ? "Credits…" : `Credits: ${label}`}
        </p>
        {updated && (
          <p className="truncate text-[10px] font-normal text-slate-500">
            Updated {updated}
            {data?.stale ? " · stale" : ""}
          </p>
        )}
      </div>
      <button
        type="button"
        onClick={() => refresh.mutate()}
        disabled={refresh.isPending || isFetching}
        aria-label="Refresh fal.ai credits"
        className="ml-0.5 rounded p-1 text-slate-500 hover:bg-white/80 hover:text-slate-800 disabled:opacity-50"
      >
        <RefreshCcw
          className={`size-3 ${refresh.isPending || isFetching ? "animate-spin" : ""}`}
        />
      </button>
    </div>
  );
}
