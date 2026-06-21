import { apiFetch, API_BASE, authHeaders, parseApiError } from "./apiClient";
import type {
  AgencyInviteCreate,
  AgencyInviteCreated,
  AgencyTeamSummary,
  AgencyUserUpdate,
  User,
} from "./types";

export async function fetchAgencyTeam(): Promise<AgencyTeamSummary> {
  const response = await apiFetch(`${API_BASE}/agency/team`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load team workspace."));
  }
  return response.json();
}

export async function createAgencyInvite(payload: AgencyInviteCreate): Promise<AgencyInviteCreated> {
  const response = await apiFetch(`${API_BASE}/agency/invites`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to issue team invitation."));
  }
  return response.json();
}

export async function updateAgencyUser(userId: number, payload: AgencyUserUpdate): Promise<User> {
  const response = await apiFetch(`${API_BASE}/agency/users/${userId}`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update team member."));
  }
  return response.json();
}

export async function cancelAgencyInvite(invitationId: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/agency/invites/${encodeURIComponent(invitationId)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to revoke invitation."));
  }
}
