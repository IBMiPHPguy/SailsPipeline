import { clearToken, getToken, setToken } from "./authStorage";
import { API_BASE, authHeaders, parseApiError } from "./apiClient";
import type { AuthResponse, RegisterInput, User } from "./types";

export async function login(username: string, password: string): Promise<AuthResponse> {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Login failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token);
  return data;
}

export async function register(payload: RegisterInput): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Registration failed."));
  }

  return response.json();
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    clearToken();
    throw new Error("Session expired.");
  }

  return response.json();
}

export function logout(): void {
  clearToken();
}

export { authHeaders, getToken };
