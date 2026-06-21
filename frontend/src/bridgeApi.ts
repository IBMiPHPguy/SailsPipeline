import { API_BASE, authHeaders, parseApiError } from "./apiClient";
import { setToken } from "./authStorage";
import type { AuthResponse, BridgeAgencySummary, BridgeLoginInput, BridgeSummary, BridgeTenantDetail, BridgeTenantUpdate, PlatformInviteCreate, PlatformInviteCreated } from "./types";

export async function loginBridge(payload: BridgeLoginInput): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/auth/bridge/login`, {
    method: "POST",
    headers: authHeaders(true, "bridge"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Login failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token, "bridge");
  return data;
}

export async function fetchBridgeSummary(): Promise<BridgeSummary> {
  const response = await fetch(`${API_BASE}/bridge/summary`, {
    headers: authHeaders(false, "bridge"),
  });
  if (response.status === 403) {
    throw new Error("Bridge access requires platform super admin role.");
  }
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load Bridge summary."));
  }
  return response.json();
}

export async function createBridgeInvite(payload: PlatformInviteCreate): Promise<PlatformInviteCreated> {
  const response = await fetch(`${API_BASE}/bridge/invites`, {
    method: "POST",
    headers: authHeaders(true, "bridge"),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to issue platform invitation."));
  }
  return response.json();
}

export async function fetchBridgeTenant(agencyId: string): Promise<BridgeTenantDetail> {
  const response = await fetch(`${API_BASE}/bridge/tenants/${encodeURIComponent(agencyId)}`, {
    headers: authHeaders(false, "bridge"),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load tenant details."));
  }
  return response.json();
}

export async function updateBridgeTenant(
  agencyId: string,
  payload: BridgeTenantUpdate,
): Promise<BridgeAgencySummary> {
  const response = await fetch(`${API_BASE}/bridge/tenants/${encodeURIComponent(agencyId)}`, {
    method: "PATCH",
    headers: authHeaders(true, "bridge"),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update tenant."));
  }
  return response.json();
}

export async function cancelBridgeInvite(invitationId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/bridge/invites/${encodeURIComponent(invitationId)}`, {
    method: "DELETE",
    headers: authHeaders(false, "bridge"),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to revoke invitation."));
  }
}
