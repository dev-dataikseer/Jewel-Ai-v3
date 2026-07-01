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
    setHasToken(!!getAccessToken());
  }, []);

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
