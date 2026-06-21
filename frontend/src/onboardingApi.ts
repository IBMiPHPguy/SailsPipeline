import { API_BASE, authHeaders, parseApiError } from "./apiClient";
import type { AuthResponse, OnboardingAcceptInput, OnboardingInvite } from "./types";

export async function verifyOnboardingInvite(token: string): Promise<OnboardingInvite> {
  const params = new URLSearchParams({ token });
  const response = await fetch(`${API_BASE}/onboarding/invites/verify?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Invitation is invalid or expired."));
  }
  return response.json();
}

export async function acceptOnboardingInvite(payload: OnboardingAcceptInput): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/onboarding/accept`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to complete onboarding."));
  }
  return response.json();
}
