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
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
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
    const res = await axios.post(`${API_BASE}/auth/refresh`, null, {
      params: { refresh_token: refresh },
    });
    const { access_token, refresh_token } = res.data;
    setTokens(access_token, refresh_token);
    return access_token;
  } catch {
    clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string; error?: string; message?: string }>) => {
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
      data?.detail ||
      data?.error ||
      data?.message ||
      (error.code === "ECONNABORTED" ? "Request timed out. Please try again." : error.message) ||
      "Request failed";

    return Promise.reject(
      Object.assign(error, { message, friendlyMessage: message })
    );
  }
);

export function mediaUrl(url?: string | null) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return url;
}
