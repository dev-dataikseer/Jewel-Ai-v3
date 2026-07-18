import axios, { type AxiosError } from "axios";

export const API_BASE = "/api";
const UPLOAD_TIMEOUT_MS = 120_000;

const ACCESS_KEY = "jewel_access_token";
const REFRESH_KEY = "jewel_refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  window.dispatchEvent(new Event("jewel-auth-change"));
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  window.dispatchEvent(new Event("jewel-auth-change"));
}

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const url = config.url || "";
  if (url.includes("/assets/upload") || url.includes("/assets/bulk-upload")) {
    config.timeout = UPLOAD_TIMEOUT_MS;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const res = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refresh });
    const { access_token, refresh_token } = res.data;
    setTokens(access_token, refresh_token);
    return access_token;
  } catch {
    clearTokens();
    return null;
  }
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
      return row.layer_errors.filter((x) => typeof x === "string").join("; ");
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
      if (isAuthMeBootstrap || requestUrl.includes("/auth/login")) {
        return Promise.reject(error);
      }
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }
      const token = await refreshPromise;
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
