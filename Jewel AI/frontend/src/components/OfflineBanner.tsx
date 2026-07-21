import { useEffect, useState } from "react";

/** Lightweight offline / reconnect banner for Studio & History. */
export function OfflineBanner() {
  const [offline, setOffline] = useState(
    typeof navigator !== "undefined" ? !navigator.onLine : false,
  );

  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (!offline) return null;
  return (
    <div
      role="status"
      className="bg-amber-50 text-amber-900 text-sm px-4 py-2 border-b border-amber-200 text-center"
    >
      You are offline. Job updates may pause until the connection returns.
    </div>
  );
}
