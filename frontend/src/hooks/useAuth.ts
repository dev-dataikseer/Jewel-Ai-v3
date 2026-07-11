import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, clearTokens, getAccessToken, setTokens } from "@/lib/api";
import type { User } from "@/types";

type LoginResponse = {
  access_token: string;
  refresh_token: string;
  user?: User;
};

export function useAuth() {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(() => !!getAccessToken());

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

  const {
    data: user,
    isLoading: userLoading,
    isError,
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
    if (hasToken && isError) {
      clearTokens();
      setHasToken(false);
      queryClient.setQueryData(["auth", "me"], null);
    }
  }, [hasToken, isError, queryClient]);

  const login = useCallback(
    async (payload: { email: string; password: string }) => {
      const { data } = await api.post<LoginResponse>("/auth/login", payload);
      setTokens(data.access_token, data.refresh_token);
      setHasToken(true);
      queryClient.setQueryData(["auth", "me"], data.user);
      return data.user;
    },
    [queryClient]
  );

  const logout = useCallback(() => {
    clearTokens();
    setHasToken(false);
    queryClient.setQueryData(["auth", "me"], null);
    queryClient.clear();
  }, [queryClient]);

  return {
    user: hasToken ? user : null,
    isLoading: hasToken && userLoading && !isError,
    isError,
    isAuthenticated: hasToken && !!user,
    isAdmin: user?.role === "admin",
    login,
    logout,
    refetch,
  };
}
