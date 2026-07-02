import { API_BASE, apiFetch, authHeaders, parseApiError } from "./apiClient";
import type {
  CcAuthCompleteResponse,
  CcAuthCardPayload,
  CcAuthPurgeResponse,
  CcAuthRevealResponse,
  CcAuthSummary,
  CcAuthValidateResponse,
} from "./types";

export async function validateCcAuthToken(token: string): Promise<CcAuthValidateResponse> {
  const response = await fetch(`${API_BASE}/cc-auth/validate/${encodeURIComponent(token)}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to verify authorization link."));
  }
  return response.json();
}

export async function completeCcAuth(
  token: string,
  card: CcAuthCardPayload,
): Promise<CcAuthCompleteResponse> {
  const response = await fetch(`${API_BASE}/cc-auth/complete/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(card),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to complete authorization."));
  }
  return response.json();
}
export function readCcAuthTokenFromPath(pathname = window.location.pathname): string {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const prefix = "/cc-auth/";
  if (!normalized.startsWith(prefix)) {
    return "";
  }
  return decodeURIComponent(normalized.slice(prefix.length)).trim();
}

export async function fetchRequestCcAuthorizations(requestId: number): Promise<CcAuthSummary[]> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/cc-auth`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load card authorizations."));
  }
  return response.json();
}

export async function revealRequestCcAuthorization(
  requestId: number,
  authorizationId: string,
  vaultAccessKey: string,
): Promise<CcAuthRevealResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/cc-auth/${authorizationId}/reveal`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ vault_access_key: vaultAccessKey }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to reveal card data."));
  }
  return response.json();
}

export async function purgeRequestCcAuthorization(
  requestId: number,
  authorizationId: string,
): Promise<CcAuthPurgeResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/cc-auth/${authorizationId}/purge`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to purge card data."));
  }
  return response.json();
}