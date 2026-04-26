const AUTH_STORAGE_KEY = "terramoist.auth.token";

function getApiBase() {
  const base = import.meta.env.VITE_API_BASE ?? "/api/v1";
  return base.replace(/\/+$/, "");
}

async function apiRequest(path, { method = "GET", body, token } = {}) {
  const response = await fetch(`${getApiBase()}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail ?? "Request failed");
  }

  return payload;
}

export function loadStoredToken() {
  return window.localStorage.getItem(AUTH_STORAGE_KEY);
}

export function persistSession(token) {
  window.localStorage.setItem(AUTH_STORAGE_KEY, token);
}

export function clearSession() {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function registerUser(form) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: form,
  });
}

export function loginUser(form) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: form,
  });
}

export function fetchCurrentUser(token) {
  return apiRequest("/auth/me", { token });
}
