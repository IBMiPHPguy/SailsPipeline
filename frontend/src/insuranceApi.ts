import { API_BASE, apiFetch, authHeaders, parseApiError } from "./apiClient";

export type InsuranceRequestStatusResponse = {
  travel_request_id: number;
  insurance_status: string;
  waiver_signed: boolean;
  waiver_signed_at: string | null;
  waiver_request_status: "none" | "pending" | "expired" | "completed";
  waiver_sent_at: string | null;
  waiver_expires_at: string | null;
  has_annual_insurance: boolean;
  annual_insurance_expires_at: string | null;
  annual_insurance_policy_number: string | null;
  annual_insurance_is_valid: boolean;
  annual_insurance_is_expired: boolean;
  primary_passenger_id: number | null;
  client_name: string;
  client_registry_passenger_id: number | null;
  has_accepted_quote: boolean;
  all_quotes_declined: boolean;
  has_proposed_quotes: boolean;
  can_complete_task: boolean;
  completion_blocked_reason: string | null;
};

export type AnnualInsuranceUpdate = {
  has_annual_insurance?: boolean;
  annual_insurance_expires_at?: string | null;
  annual_insurance_policy_number?: string | null;
};

export type InsuranceWaiverValidateResponse = {
  valid: boolean;
  passenger_name: string;
  passenger_email: string;
  agency_name: string;
  waiver_text: string;
  expires_at: string;
  request_id: number;
};

export type InsuranceWaiverSignResponse = {
  message: string;
  signed: boolean;
};

export type SendInsuranceWaiverEmailResponse = {
  message: string;
  portal_url: string;
  email_sent: boolean;
  recipient: string;
};

export async function fetchInsuranceStatusForRequest(
  requestId: number,
): Promise<InsuranceRequestStatusResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/insurance/status`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load insurance status."));
  }
  return response.json();
}

export async function updateAnnualInsurance(
  requestId: number,
  payload: AnnualInsuranceUpdate,
): Promise<InsuranceRequestStatusResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/insurance/annual`, {
    method: "PATCH",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to update annual insurance."));
  }
  return response.json();
}

export async function clearExpiredAnnualInsurance(
  requestId: number,
): Promise<InsuranceRequestStatusResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/insurance/clear-annual`, {
    method: "POST",
    headers: authHeaders(true),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to clear annual insurance."));
  }
  return response.json();
}

export async function sendInsuranceWaiverEmail(requestId: number): Promise<SendInsuranceWaiverEmailResponse> {
  const response = await apiFetch(`${API_BASE}/insurance/send-waiver`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ travel_request_id: requestId }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to send insurance waiver email."));
  }
  return response.json();
}

export async function validateInsuranceWaiverToken(token: string): Promise<InsuranceWaiverValidateResponse> {
  const response = await fetch(`${API_BASE}/insurance/validate/${encodeURIComponent(token)}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to verify insurance waiver link."));
  }
  return response.json();
}

export async function signInsuranceWaiver(token: string): Promise<InsuranceWaiverSignResponse> {
  const response = await fetch(`${API_BASE}/insurance/waiver/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to record insurance waiver signature."));
  }
  return response.json();
}

export function readInsuranceTokenFromPath(pathname = window.location.pathname): string {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const prefix = "/insurance-auth/";
  if (!normalized.startsWith(prefix)) {
    return "";
  }
  return decodeURIComponent(normalized.slice(prefix.length)).trim();
}
