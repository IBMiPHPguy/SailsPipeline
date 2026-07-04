import { clearToken, getToken, setToken, type AuthScope } from "./authStorage";
import { API_BASE, apiFetch, authHeaders, parseApiError, redirectToSubscriptionRestore } from "./apiClient";
import type { AuthResponse, LoginInput, PublicRegisterInput, RegisterInput, User } from "./types";

export async function login(payload: LoginInput): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    if (
      response.status === 403 &&
      payload?.detail &&
      typeof payload.detail === "object" &&
      payload.detail.lock_reason === "trial_expired"
    ) {
      redirectToSubscriptionRestore(
        typeof payload.detail.subscription_state === "string" ? payload.detail.subscription_state : "Locked",
        "trial_expired",
      );
      throw new Error(
        typeof payload.detail.message === "string"
          ? payload.detail.message
          : "Your SailsPipeline demo has ended.",
      );
    }

    throw new Error(await parseApiError(response, "Login failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token, "crm");
  return data;
}

export async function register(payload: RegisterInput): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Registration failed."));
  }

  return response.json();
}

export async function registerAgencyWorkspace(payload: PublicRegisterInput): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE}/public/register`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Agency registration failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token, "crm");
  return data;
}

export async function fetchCurrentUser(scope: AuthScope = "crm"): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(false, scope),
  });

  if (!response.ok) {
    clearToken(scope);
    throw new Error("Session expired.");
  }

  return response.json();
}

export function logout(scope: AuthScope = "crm"): void {
  clearToken(scope);
}

export { authHeaders, getToken };