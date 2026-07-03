import { API_BASE, apiFetch, authHeaders, parseApiError } from "./apiClient";

export type AgencySettings = {
  agency_id: string;
  agency_name: string;
  brand_logo_url?: string | null;
  primary_color: string;
  secondary_color: string;
  custom_master_tc?: string | null;
  email_signature_block?: string | null;
  business_address?: string | null;
  business_phone?: string | null;
};

export type AgencySettingsUpdate = {
  agency_name?: string;
  primary_color?: string;
  secondary_color?: string;
  custom_master_tc?: string | null;
  email_signature_block?: string | null;
  business_address?: string | null;
  business_phone?: string | null;
};

export type AgencyLogoUploadResponse = {
  brand_logo_url: string;
  message: string;
};

export type AgencySignatureImageUploadResponse = {
  image_url: string;
  message: string;
};

export type AgencyBrandingChrome = {
  agency_name: string;
  brand_logo_url?: string | null;
  primary_color: string;
  secondary_color: string;
};

export async function fetchAgencyBrandingChrome(): Promise<AgencyBrandingChrome> {
  const response = await apiFetch(`${API_BASE}/agency/branding`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load agency branding."));
  }
  return response.json();
}

export async function fetchAgencySettings(): Promise<AgencySettings> {
  const response = await apiFetch(`${API_BASE}/agency/settings`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to load agency settings."));
  }
  return response.json();
}

export async function updateAgencySettings(payload: AgencySettingsUpdate): Promise<AgencySettings> {
  const response = await apiFetch(`${API_BASE}/agency/settings`, {
    method: "PUT",
    headers: authHeaders(true),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to save agency settings."));
  }
  return response.json();
}

export async function uploadAgencyLogo(file: File): Promise<AgencyLogoUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE}/agency/settings/upload-logo`, {
    method: "POST",
    headers: authHeaders(false),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload brand logo."));
  }
  return response.json();
}

export async function uploadAgencySignatureImage(file: File): Promise<AgencySignatureImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE}/agency/settings/upload-signature-image`, {
    method: "POST",
    headers: authHeaders(false),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload signature image."));
  }
  return response.json();
}
