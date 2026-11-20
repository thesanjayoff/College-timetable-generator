import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { authApi } from "../api/auth";
import { clearToken, getToken, onUnauthorized, setToken } from "../api/client";
import type { UserOut, UserRole } from "../api/types";

interface AuthContextValue {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  isAdmin: boolean;
  isCoordinator: boolean;
  isViewer: boolean;
  /** True for admin or coordinator — roles that can create/edit/delete most resources. */
  canWrite: boolean;
  hasRole: (...roles: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  useEffect(() => {
    return onUnauthorized(() => {
      setUser(null);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const token = await authApi.login(email, password);
    setToken(token.access_token);
    const me = await authApi.me();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const role = user?.role;
    return {
      user,
      loading,
      login,
      logout,
      refreshUser: loadUser,
      isAdmin: role === "admin",
      isCoordinator: role === "coordinator",
      isViewer: role === "viewer",
      canWrite: role === "admin" || role === "coordinator",
      hasRole: (...roles: UserRole[]) => !!role && roles.includes(role),
    };
  }, [user, loading, login, logout, loadUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
