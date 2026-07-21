import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { mediaUrl } from "@/lib/api";
import axios from "axios";

type SharePayload = {
  workflow: string;
  output_url?: string | null;
  output_urls?: string[] | null;
  jewelry_type?: string | null;
  created_at?: string;
};

export function SharePage() {
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["public-share", token],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await axios.get<SharePayload>(`/api/public/share/${token}`);
      return res.data;
    },
  });

  const urls = (() => {
    const multi = (data?.output_urls || []).filter(Boolean) as string[];
    if (multi.length) return multi;
    return data?.output_url ? [data.output_url] : [];
  })();

  return (
    <div className="min-h-screen bg-slate-50 font-sans">
      <header className="border-b border-slate-200 bg-white px-4 py-4">
        <p className="text-sm font-semibold text-slate-900">Jewel AI — Shared generation</p>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        {isLoading && (
          <p className="text-sm text-slate-500">Loading shared image…</p>
        )}
        {error && (
          <p className="text-sm text-rose-600">
            This share link is invalid or expired.
          </p>
        )}
        {data && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium text-slate-500">
                {data.workflow}
                {data.jewelry_type ? ` · ${data.jewelry_type}` : ""}
              </p>
              <div className="mt-3 flex flex-col gap-3">
                {urls.length === 0 ? (
                  <p className="text-sm text-slate-500">No image available.</p>
                ) : (
                  urls.map((url) => (
                    <div
                      key={url}
                      className="flex items-center justify-center rounded-xl bg-slate-950 p-3"
                    >
                      <img
                        src={mediaUrl(url)}
                        alt={`${data.workflow}${data.jewelry_type ? ` — ${data.jewelry_type}` : ""} shared output`}
                        className="max-h-[70vh] max-w-full object-contain rounded"
                      />
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
