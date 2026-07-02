import { API_BASE, apiFetch, authHeaders, parseApiError } from "./apiClient";

export type TermsValidateResponse = {
  valid: boolean;
  passenger_name: string;
  passenger_email: string;
  agency_name: string;
  terms_text: string;
  expires_at: string;
  request_id: string;
};

export type TermsAcceptResponse = {
  message: string;
  accepted: boolean;
};

export type TermsRequestStatusResponse = {
  on_file: boolean;
  client_id: number;
  agency_id: string;
  travel_request_id?: number;
  accepted_at?: string | null;
  version_hash?: string | null;
  ip_address?: string | null;
  task_auto_completed?: boolean;
};

export type SendMasterTermsEmailResponse = {
  message: string;
  portal_url: string;
  email_sent: boolean;
  recipient: string;
};

export async function validateTermsToken(token: string): Promise<TermsValidateResponse> {
  const response = await fetch(`${API_BASE}/terms/validate/${encodeURIComponent(token)}`);
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to verify terms acceptance link."));
  }
  return response.json();
}

export async function acceptMasterTerms(token: string): Promise<TermsAcceptResponse> {
  const response = await fetch(`${API_BASE}/terms/accept/${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to record terms acceptance."));
  }
  return response.json();
}

export function readTermsTokenFromPath(pathname = window.location.pathname): string {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const prefix = "/accept-terms/";
  if (!normalized.startsWith(prefix)) {
    return "";
  }
  return decodeURIComponent(normalized.slice(prefix.length)).trim();
}

export async function fetchTermsStatusForRequest(requestId: number): Promise<TermsRequestStatusResponse> {
  const response = await apiFetch(`${API_BASE}/requests/${requestId}/terms/status`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load Master Terms status."));
  }
  return response.json();
}

export async function sendMasterTermsEmail(requestId: number): Promise<SendMasterTermsEmailResponse> {
  const response = await apiFetch(`${API_BASE}/terms/send`, {
    method: "POST",
    headers: authHeaders(true),
    body: JSON.stringify({ travel_request_id: requestId }),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to send Master Terms review email."));
  }
  return response.json();
}
