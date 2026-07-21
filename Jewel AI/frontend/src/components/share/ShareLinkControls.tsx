import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";

type ShareLinkItem = {
  id: string;
  job_id: string;
  token: string;
  expires_at?: string | null;
  views?: number;
  created_at?: string;
};

type Props = {
  jobId: string;
  /** Compact overflow-style control (Studio ResultsTray). */
  compact?: boolean;
};

export function ShareLinkControls({ jobId, compact }: Props) {
  const queryClient = useQueryClient();
  const queryKey = ["share-links", jobId] as const;

  const { data } = useQuery({
    queryKey,
    queryFn: async () =>
      (await api.get<{ items: ShareLinkItem[] }>("/share-links", { params: { job_id: jobId } }))
        .data,
  });

  const links = data?.items ?? [];

  const createMutation = useMutation({
    mutationFn: async () =>
      (
        await api.post<{ id: string; token: string }>("/share-links", {
          job_id: jobId,
        })
      ).data,
    onSuccess: async (res) => {
      const shareUrl = `${window.location.origin}/share/${res.token}`;
      try {
        await navigator.clipboard.writeText(shareUrl);
        toast.success("Share link copied");
      } catch {
        toast.success("Share link created");
      }
      await queryClient.invalidateQueries({ queryKey });
    },
    onError: () => toast.error("Could not create share link"),
  });

  const revokeMutation = useMutation({
    mutationFn: async (shareId: string) => {
      await api.delete(`/share-links/${shareId}`);
      return shareId;
    },
    onSuccess: async () => {
      toast.success("Share link revoked");
      await queryClient.invalidateQueries({ queryKey });
    },
    onError: () => toast.error("Could not revoke share link"),
  });

  if (compact) {
    return (
      <div className="space-y-1">
        <button
          type="button"
          className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-jewel-ink hover:bg-jewel-muted"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending}
        >
          <Link2 className="size-3.5" />
          {createMutation.isPending ? "Creating…" : "Share link"}
        </button>
        {links.map((link) => (
          <button
            key={link.id}
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-rose-700 hover:bg-rose-50"
            onClick={() => revokeMutation.mutate(link.id)}
            disabled={revokeMutation.isPending}
          >
            <Trash2 className="size-3.5" />
            Revoke · {link.token.slice(0, 8)}…
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        className="ui-btn-secondary"
        onClick={() => createMutation.mutate()}
        disabled={createMutation.isPending}
      >
        <Link2 className="size-3.5" />
        {createMutation.isPending ? "Creating…" : "Share"}
      </button>
      {links.map((link) => (
        <button
          key={link.id}
          type="button"
          className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 text-xs font-semibold text-rose-700 hover:bg-rose-100"
          onClick={() => revokeMutation.mutate(link.id)}
          disabled={revokeMutation.isPending}
          title={`Revoke share ${link.token.slice(0, 8)}`}
        >
          <Trash2 className="size-3.5" />
          Revoke
        </button>
      ))}
    </div>
  );
}
