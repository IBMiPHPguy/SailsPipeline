import { getToken, type AuthScope } from "./authStorage";

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";
export const SUBSCRIPTION_RESTORE_PATH = "/subscription-restore";

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

export function authHeaders(includeJson = false, scope: AuthScope = "crm"): HeadersInit {
  const headers: Record<string, string> = {};
  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }

  const token = getToken(scope);
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export function redirectToSubscriptionRestore(subscriptionState?: string, reason?: string) {
  if (window.location.pathname.replace(/\/+$/, "") === SUBSCRIPTION_RESTORE_PATH) {
    return;
  }

  const params = new URLSearchParams();
  if (subscriptionState) {
    params.set("state", subscriptionState);
  }
  if (reason) {
    params.set("reason", reason);
  }
  const query = params.toString();
  window.location.replace(query ? `${SUBSCRIPTION_RESTORE_PATH}?${query}` : SUBSCRIPTION_RESTORE_PATH);
}

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 402) {
    const payload = await response.clone().json().catch(() => ({}));
    redirectToSubscriptionRestore(
      typeof payload.subscription_state === "string" ? payload.subscription_state : undefined,
      typeof payload.lock_reason === "string" ? payload.lock_reason : undefined,
    );
  }
  return response;
}
