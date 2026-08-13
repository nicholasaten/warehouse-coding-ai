"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiJson } from "./api-client";
import { setAccessToken } from "./token-store";

export type CurrentUser = {
  id: string;
  full_name: string;
  email: string;
  role: "admin" | "pic";
  site_id: string | null;
};

type LoginResponse = {
  access_token: string;
  user: CurrentUser;
};

type AuthState = {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // On first load, try the httpOnly refresh cookie to silently resume a
    // session across reloads -- /auth/refresh returns the user profile
    // inline, so this is the only request needed here.
    (async () => {
      try {
        const data = await apiJson<LoginResponse>("/auth/refresh", { method: "POST" });
        setAccessToken(data.access_token);
        setUser(data.user);
      } catch {
        setAccessToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiJson<LoginResponse>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiJson("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ user, isLoading, login, logout }), [user, isLoading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
