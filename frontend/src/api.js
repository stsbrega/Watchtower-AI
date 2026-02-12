/**
 * Watchtower AI - API helpers
 * Authenticated fetch and WebSocket helpers with token management.
 */

const TOKEN_KEY = "watchtower_token";

/** Get stored auth token */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

/** Store auth token */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

/** Remove auth token */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/** Check if we have a token */
export function hasToken() {
  return !!getToken();
}

/**
 * Authenticated fetch wrapper.
 * Automatically adds Authorization header and handles 401s.
 */
export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("auth:logout"));
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Create an authenticated WebSocket connection.
 * Passes the JWT as a query parameter.
 */
export function createAuthWS(path) {
  const token = getToken();
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${location.host}${path}${token ? `?token=${token}` : ""}`;
  return new WebSocket(url);
}
