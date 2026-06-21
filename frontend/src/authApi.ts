import { clearToken, getToken, setToken, type AuthScope } from "./authStorage";
import { API_BASE, apiFetch, authHeaders, parseApiError } from "./apiClient";
import type { AuthResponse, LoginInput, RegisterInput, User } from "./types";

export async function login(payload: LoginInput): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
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