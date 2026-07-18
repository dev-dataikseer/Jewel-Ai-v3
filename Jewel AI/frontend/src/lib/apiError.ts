/** Shared API error toast helper — prefers axios friendlyMessage from api.ts interceptor. */

export function apiErrorMessage(err: unknown, fallback = "Request failed"): string {
  if (!err) return fallback;
  if (typeof err === "string") return err;
  if (err instanceof Error) {
    const friendly = (err as Error & { friendlyMessage?: string }).friendlyMessage;
    if (friendly) return friendly;
    if (err.message) return err.message;
  }
  if (typeof err === "object" && err !== null) {
    const row = err as { friendlyMessage?: string; message?: string };
    if (row.friendlyMessage) return row.friendlyMessage;
    if (row.message) return row.message;
  }
  return fallback;
}
