import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { apiErrorMessage } from "@/lib/apiError";

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

function formatBalance(balance: number) {
  try {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(balance);
  } catch {
    return Number(balance ?? 0).toFixed(2);
  }
}

export function FalCreditsWidget() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["billing", "fal-credits"],
    queryFn: async () =>
      (await api.get<FalCreditsResponse>("/billing/fal-credits")).data,
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
    retry: 1,
  });

  const refresh = useMutation({
    mutationFn: async () =>
      (await api.post<FalCreditsResponse>("/billing/fal-credits/refresh")).data,
    onSuccess: (next) => {
      queryClient.setQueryData(["billing", "fal-credits"], next);
      if (next?.available && next.current_balance != null) {
        toast.success(`Credits updated: ${formatBalance(next.current_balance)}`);
      } else if (next?.error) {
        toast.error(next.error);
      }
    },
    onError: (err) => {
      toast.error(apiErrorMessage(err as Error, "Could not refresh fal credits"));
    },
  });

  const showLow = Boolean(data?.low_balance && data.available);
  const balanceLabel =
    data?.available && data.current_balance != null
      ? formatBalance(data.current_balance)
      : isLoading
        ? "…"
        : "—";

  const titleHint = data?.error
    ? `Last error: ${data.error}`
    : data?.username
      ? `fal.ai account: ${data.username}`
      : "Refresh fal.ai credit balance";

  return (
    <div
      className={`relative inline-flex items-center gap-2 rounded-xl border bg-white py-1.5 pl-3 pr-8 ${
        showLow
          ? "border-amber-200"
          : data?.available
            ? "border-[var(--jewel-border)]"
            : "border-rose-200"
      }`}
      title={titleHint}
    >
      {showLow || (!data?.available && data?.error) ? (
        <AlertTriangle className="size-3.5 shrink-0 text-amber-600" aria-hidden />
      ) : null}
      <div className="min-w-0 leading-tight">
        <p className="text-[10px] font-medium text-[var(--jewel-ink-muted)] leading-none">
          Credits Balance
        </p>
        <p className="mt-0.5 text-[15px] font-bold text-[var(--jewel-ink)] leading-none tabular-nums">
          {balanceLabel}
        </p>
      </div>
      <button
        type="button"
        aria-label="Refresh fal credits"
        title="Refresh from fal.ai"
        disabled={refresh.isPending}
        onClick={() => refresh.mutate()}
        className="absolute -right-2 top-1/2 -translate-y-1/2 inline-flex size-7 items-center justify-center rounded-lg text-white shadow-[var(--jewel-shadow-cta)] disabled:opacity-70"
        style={{ backgroundImage: "var(--jewel-grad-cta)" }}
      >
        <RefreshCw
          className={`size-3.5 stroke-[2.5] ${refresh.isPending ? "animate-spin" : ""}`}
        />
      </button>
    </div>
  );
}
