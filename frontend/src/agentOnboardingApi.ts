import { API_BASE, authHeaders, parseApiError } from "./apiClient";
import type { AgentInvite, AuthResponse, OnboardingAcceptInput } from "./types";

export async function verifyAgentInvite(token: string): Promise<AgentInvite> {
  const params = new URLSearchParams({ token });
  const response = await fetch(`${API_BASE}/onboarding/agent/invites/verify?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Invitation is invalid or expired."));
  }
  return response.json();
}

export async function acceptAgentInvite(payload: OnboardingAcceptInput): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/onboarding/agent/accept`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to complete agent registration."));
  }
  return response.json();
}
