const API_BASE = "/api/v1";
const USER_KEY = "tms_user";
const LEGACY_TOKEN_KEY = "tms_access_token";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE_NAMES = ["tms_csrf", "__Host-tms_csrf"];
const AUTH_PATHS_WITHOUT_REFRESH = new Set(["/auth/login", "/auth/token", "/auth/refresh"]);
let refreshPromise = null;

export class ApiError extends Error {
  constructor(message, status, data = null, { retryAfter = null, requestId = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    this.retryAfter = retryAfter;
    this.requestId = requestId;
  }
}

function cookieValue(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!item) return null;
  try {
    return decodeURIComponent(item.slice(prefix.length));
  } catch {
    return item.slice(prefix.length);
  }
}

function csrfToken() {
  for (const name of CSRF_COOKIE_NAMES) {
    const value = cookieValue(name);
    if (value) return value;
  }
  return null;
}

function detailMessage(data, status) {
  if (typeof data === "string" && data.trim()) return data.trim();
  const detail = data?.detail;

  if (typeof detail === "string" && detail) return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    return detail.message || detail.detail || `Erro HTTP ${status}`;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || "Valor inválido")
      .join("; ");
  }
  return `Erro HTTP ${status}`;
}

function passwordChangeRequired(data) {
  return data?.detail?.code === "password_change_required";
}

async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (response.status === 204) return null;
  return contentType.includes("application/json")
    ? response.json()
    : response.text();
}

function buildFetchOptions(options = {}) {
  const headers = new Headers(options.headers || {});
  let body = options.body;
  const method = String(options.method || "GET").toUpperCase();

  headers.set("Accept", "application/json");
  if (
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData) &&
    !(body instanceof URLSearchParams) &&
    typeof body !== "string"
  ) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  if (UNSAFE_METHODS.has(method)) {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }

  return {
    ...options,
    method,
    headers,
    body,
    credentials: "same-origin",
    cache: options.cache || (method === "GET" ? "no-store" : "no-cache"),
  };
}

async function fetchApi(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, buildFetchOptions(options));
  const data = await readResponse(response);
  return { response, data };
}

function asApiError(response, data) {
  const retryHeader = Number.parseInt(response.headers.get("retry-after") || "", 10);
  const requestId = response.headers.get("x-request-id") || data?.request_id || null;
  return new ApiError(detailMessage(data, response.status), response.status, data, {
    retryAfter: Number.isFinite(retryHeader) ? retryHeader : null,
    requestId,
  });
}

async function refreshDirectly() {
  // Outra aba pode ter renovado a sessao enquanto esta aba aguardava o lock.
  const current = await fetchApi("/auth/me", { method: "GET" });
  if (current.response.ok) {
    storeUser(current.data);
    return true;
  }

  const refreshed = await fetchApi("/auth/refresh", { method: "POST" });
  if (refreshed.response.ok) {
    storeUser(refreshed.data?.user || null);
    return true;
  }

  // Em navegadores sem Web Locks, duas abas podem renovar ao mesmo tempo.
  // A segunda recebe 409, nunca um novo refresh token. Os cookies definidos
  // pela primeira aba sao compartilhados; basta confirmar a sessao atual.
  if (
    refreshed.response.status === 409 &&
    refreshed.data?.detail?.code === "refresh_already_rotated"
  ) {
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    const recovered = await fetchApi("/auth/me", { method: "GET" });
    if (recovered.response.ok) {
      storeUser(recovered.data);
      return true;
    }
  }
  return false;
}

async function refreshSession() {
  if (refreshPromise) return refreshPromise;

  const operation = async () => {
    try {
      if (navigator.locks?.request) {
        return await navigator.locks.request("tms-session-refresh", refreshDirectly);
      }
      return await refreshDirectly();
    } catch {
      return false;
    }
  };

  refreshPromise = operation().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

export function getStoredUser() {
  try {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

export function storeUser(user) {
  if (user) sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  else sessionStorage.removeItem(USER_KEY);

  // Remove credenciais de versoes antigas. O JWT atual fica somente em cookie
  // HttpOnly e, portanto, nao pode ser lido por JavaScript.
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function clearSession() {
  sessionStorage.removeItem(USER_KEY);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function api(path, options = {}) {
  const {
    redirectOnUnauthorized = true,
    redirectOnPasswordChange = true,
    refreshOnUnauthorized = true,
    _retriedAfterRefresh = false,
    ...fetchOptions
  } = options;

  let { response, data } = await fetchApi(path, fetchOptions);

  const mayRefresh =
    response.status === 401 &&
    refreshOnUnauthorized &&
    !_retriedAfterRefresh &&
    !AUTH_PATHS_WITHOUT_REFRESH.has(path);

  if (mayRefresh && (await refreshSession())) {
    ({ response, data } = await fetchApi(path, fetchOptions));
  }

  if (!response.ok) {
    const error = asApiError(response, data);

    if (response.status === 401 && redirectOnUnauthorized) {
      clearSession();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.replace("/login?session=expired");
      }
    } else if (
      response.status === 403 &&
      passwordChangeRequired(data) &&
      redirectOnPasswordChange &&
      !window.location.pathname.startsWith("/change-password")
    ) {
      window.location.replace("/change-password");
    }

    throw error;
  }

  return data;
}

export async function login(email, password) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const data = await api("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
    redirectOnUnauthorized: false,
    redirectOnPasswordChange: false,
    refreshOnUnauthorized: false,
  });

  storeUser(data.user);
  return data.user;
}

export async function logout() {
  try {
    await api("/auth/logout", {
      method: "POST",
      redirectOnUnauthorized: false,
      redirectOnPasswordChange: false,
      refreshOnUnauthorized: false,
    });
  } finally {
    clearSession();
  }
}

export async function logoutAll() {
  try {
    await api("/auth/logout-all", {
      method: "POST",
      redirectOnPasswordChange: false,
    });
  } finally {
    clearSession();
  }
}

export async function changePassword(currentPassword, newPassword) {
  await api("/auth/change-password", {
    method: "POST",
    body: {
      current_password: currentPassword,
      new_password: newPassword,
    },
    redirectOnPasswordChange: false,
  });
  clearSession();
}
