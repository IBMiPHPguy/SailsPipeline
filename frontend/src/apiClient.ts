import { getToken } from "./authStorage";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

export async function parseApiError(response: Response, fallback: string): Promise<string> {
  const error = await response.json().catch(() => ({ detail: fallback }));
  if (Array.isArray(error.detail)) {
    return (
      error.detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join(" ") || fallback
    );
  }
  return typeof error.detail === "string" ? error.detail : fallback;
}

export function authHeaders(includeJson = false): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}
