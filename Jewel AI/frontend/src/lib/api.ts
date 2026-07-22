import axios, { type AxiosError } from "axios";

export const API_BASE = "/api";
const UPLOAD_TIMEOUT_MS = 120_000;

const LEGACY_ACCESS_KEY = "jewel_access_token";
const LEGACY_REFRESH_KEY = "jewel_refresh_token";
const CSRF_COOKIE = "jewel_csrf";

/** Access token kept in memory only (not localStorage) to reduce XSS exfil risk. */
let memoryAccessToken: string | null = null;

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function getAccessToken(): string | null {
  return memoryAccessToken;
}

export function getCsrfToken(): string | null {
  return readCookie(CSRF_COOKIE);
}

/** @deprecated Refresh lives in httpOnly cookie; kept for logout body fallback. */
export function getRefreshToken(): string | null {
  return null;
}

export function setTokens(access: string, _refresh?: string) {
  memoryAccessToken = access;
  // Clear any legacy localStorage tokens from older clients.
  try {
    localStorage.removeItem(LEGACY_ACCESS_KEY);
    localStorage.removeItem(LEGACY_REFRESH_KEY);
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event("jewel-auth-change"));
}

export function clearTokens() {
  memoryAccessToken = null;
  try {
    localStorage.removeItem(LEGACY_ACCESS_KEY);
    localStorage.removeItem(LEGACY_REFRESH_KEY);
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event("jewel-auth-change"));
}

// Migrate away from legacy localStorage on boot.
try {
  const legacy = localStorage.getItem(LEGACY_ACCESS_KEY);
  if (legacy) {
    memoryAccessToken = legacy;
    localStorage.removeItem(LEGACY_ACCESS_KEY);
    localStorage.removeItem(LEGACY_REFRESH_KEY);
  }
} catch {
  /* ignore */
}

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const csrf = getCsrfToken();
  if (csrf) {
    config.headers["X-CSRF-Token"] = csrf;
  }
  const url = config.url || "";
  if (url.includes("/assets/upload") || url.includes("/assets/bulk-upload")) {
    config.timeout = UPLOAD_TIMEOUT_MS;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function doRefreshAccessToken(): Promise<string | null> {
  try {
    const res = await axios.post(
      `${API_BASE}/auth/refresh`,
      {},
      {
        withCredentials: true,
        headers: { "X-CSRF-Token": getCsrfToken() || "" },
      },
    );
    const { access_token, refresh_token } = res.data;
    setTokens(access_token, refresh_token);
    return access_token;
  } catch (err) {
    // Only clear session on definitive auth rejection — keep tokens on network/5xx.
    if (axios.isAxiosError(err) && err.response?.status === 401) {
      clearTokens();
    }
    return null;
  }
}

/** Shared refresh with mutex so StrictMode double-mount / interceptor share one in-flight call. */
export function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

/** FastAPI `detail` can be a string, list of validation errors, or `{field, message}`. */
export function formatApiDetail(detail: unknown): string | undefined {
  if (detail == null) return undefined;
  if (typeof detail === "string") return detail;
  if (typeof detail === "number" || typeof detail === "boolean") return String(detail);
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object") {
        const row = item as { loc?: unknown[]; msg?: string; message?: string; field?: string };
        const where = Array.isArray(row.loc) ? row.loc.filter((x) => x !== "body").join(".") : row.field;
        const text = row.msg || row.message;
        if (text && where) return `${where}: ${text}`;
        if (text) return text;
      }
      try {
        return JSON.stringify(item);
      } catch {
        return "Invalid request";
      }
    });
    return parts.filter(Boolean).join("; ") || undefined;
  }
  if (typeof detail === "object") {
    const row = detail as {
      message?: unknown;
      field?: unknown;
      error?: unknown;
      detail?: unknown;
      layer_errors?: unknown;
    };
    if (Array.isArray(row.layer_errors)) {
      return row.layer_errors.filter((x) => typeof x === "string").join("; ") as string;
    }
    if (typeof row.message === "string") {
      return typeof row.field === "string" && row.field
        ? `${row.field}: ${row.message}`
        : row.message;
    }
    if (typeof row.error === "string") return row.error;
    if (typeof row.detail === "string") return row.detail;
    try {
      return JSON.stringify(detail);
    } catch {
      return "Request failed";
    }
  }
  return undefined;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: unknown; error?: unknown; message?: unknown }>) => {
    const original = error.config;
    const requestUrl = original?.url || "";
    const isAuthMeBootstrap = requestUrl.includes("/auth/me") && !getAccessToken();

    if (error.response?.status === 401 && original && !original.headers["X-Retry"]) {
      if (isAuthMeBootstrap || requestUrl.includes("/auth/login") || requestUrl.includes("/auth/refresh")) {
        return Promise.reject(error);
      }
      const token = await refreshAccessToken();
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        original.headers["X-Retry"] = "1";
        return api.request(original);
      }
    }

    const data = error.response?.data;
    const message =
      formatApiDetail(data?.detail) ||
      formatApiDetail(data?.error) ||
      formatApiDetail(data?.message) ||
      (error.code === "ECONNABORTED" ? "Request timed out. Please try again." : undefined) ||
      (typeof error.message === "string" ? error.message : undefined) ||
      "Request failed";

    return Promise.reject(Object.assign(error, { message, friendlyMessage: message }));
  }
);

/** Resolve media paths; signed /uploads URLs from API already include query params. */
export function mediaUrl(url?: string | null) {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/uploads/") || url.startsWith("/api/")) return url;
  if (url.startsWith("uploads/")) return `/${url}`;
  return url;
}

/** Gallery thumbnail via Pillow resize endpoint (falls back to full mediaUrl). */
export function thumbUrl(url?: string | null, max = 400) {
  if (!url) return "";
  const resolved = mediaUrl(url);
  if (resolved.startsWith("http://") || resolved.startsWith("https://")) {
    try {
      const parsed = new URL(resolved);
      if (!parsed.pathname.startsWith("/uploads/")) return resolved;
      const filePath = parsed.pathname.replace(/^\/uploads\//, "");
      const params = new URLSearchParams(parsed.search);
      params.set("path", filePath);
      params.set("max", String(max));
      return `/api/media/thumb?${params.toString()}`;
    } catch {
      return resolved;
    }
  }
  const [pathPart, query = ""] = resolved.split("?");
  if (!pathPart.startsWith("/uploads/")) return resolved;
  const filePath = pathPart.replace(/^\/uploads\//, "");
  const params = new URLSearchParams(query);
  params.set("path", filePath);
  params.set("max", String(max));
  return `/api/media/thumb?${params.toString()}`;
}
