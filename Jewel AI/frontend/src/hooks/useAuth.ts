import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import {
  api,
  clearTokens,
  getAccessToken,
  refreshAccessToken,
  setTokens,
} from "@/lib/api";
import type { User } from "@/types";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user?: User;
};

function isAuthFailure(err: unknown): boolean {
  const status = axios.isAxiosError(err) ? err.response?.status : undefined;
  return status === 401 || status === 403;
}

export function useAuth() {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => !!getAccessToken());
  const [bootstrapping, setBootstrapping] = useState(() => !getAccessToken());

  useEffect(() => {
    const sync = () => {
      const token = !!getAccessToken();
      setHasToken(token);
      if (!token) {
        queryClient.setQueryData(["auth", "me"], null);
      }
    };
    sync();
    window.addEventListener("jewel-auth-change", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("jewel-auth-change", sync);
      window.removeEventListener("storage", sync);
    };
  }, [queryClient]);

  // Restore session from httpOnly refresh cookie after full page reload.
  // Uses shared refreshAccessToken so StrictMode double-mount shares the mutex.
  useEffect(() => {
    if (getAccessToken()) {
      setBootstrapping(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const token = await refreshAccessToken();
        if (!cancelled && token) {
          setHasToken(true);
        }
      } catch {
        /* no session */
      } finally {
        if (!cancelled) setBootstrapping(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const {
    data: user,
    isLoading: userLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const res = await api.get<User>("/auth/me");
      return res.data;
    },
    retry: false,
    enabled: hasToken,
    staleTime: 1000 * 60 * 5,
  });

  useEffect(() => {
    // Only clear session on real auth failures — keep tokens on network/5xx.
    if (hasToken && isError && isAuthFailure(error)) {
      clearTokens();
      setHasToken(false);
      queryClient.setQueryData(["auth", "me"], null);
    }
  }, [hasToken, isError, error, queryClient]);

  const login = useCallback(
    async (payload: { email: string; password: string; otp?: string; backup_code?: string }) => {
      const { data } = await api.post<LoginResponse>("/auth/login", payload);
      setTokens(data.access_token, data.refresh_token);
      setHasToken(true);
      queryClient.setQueryData(["auth", "me"], data.user);
      return data.user;
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout", {});
    } catch {
      // Best-effort revoke; always clear local session.
    }
    clearTokens();
    setHasToken(false);
    queryClient.setQueryData(["auth", "me"], null);
    queryClient.clear();
  }, [queryClient]);

  // On non-auth /auth/me errors, keep loading so AuthGuard waits instead of redirecting.
  const isLoading =
    bootstrapping ||
    (hasToken && userLoading) ||
    (hasToken && isError && !isAuthFailure(error));

  return {
    user: hasToken ? user : null,
    isLoading,
    isError,
    isAuthenticated: hasToken && !!user,
    isAdmin: user?.role === "admin",
    login,
    logout,
    refetch,
  };
}
