/**
 * Watchtower AI - Auth State Management
 * Provides login, register, logout, and user state via React context.
 */

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiFetch, setToken, clearToken, hasToken, getToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch current user on mount (if token exists)
  useEffect(() => {
    if (!hasToken()) {
      setLoading(false);
      return;
    }

    apiFetch("/api/v1/auth/me")
      .then((data) => {
        setUser(data);
        setLoading(false);
      })
      .catch(() => {
        clearToken();
        setLoading(false);
      });
  }, []);

  // Listen for forced logout (401 responses)
  useEffect(() => {
    const handler = () => {
      setUser(null);
      setError(null);
    };
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, []);

  const login = useCallback(async (email, password) => {
    setError(null);
    try {
      const res = await apiFetch("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setToken(res.access_token);

      // Fetch user profile
      const me = await apiFetch("/api/v1/auth/me");
      setUser(me);
      return me;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const register = useCallback(async (email, password, name) => {
    setError(null);
    try {
      const res = await apiFetch("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, name: name || undefined }),
      });
      setToken(res.access_token);

      // Fetch user profile
      const me = await apiFetch("/api/v1/auth/me");
      setUser(me);
      return me;
    } catch (e) {
      setError(e.message);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setError(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
