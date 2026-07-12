import { clearToken, getToken, setToken, type AuthScope } from "./authStorage";
import { setLastOrganizationHandle } from "./organizationHandleStorage";
import { API_BASE, apiFetch, authHeaders, parseApiError, redirectToSubscriptionRestore } from "./apiClient";
import type {
  AuthResponse,
  ForgotPasswordInput,
  LoginInput,
  PublicRegisterInput,
  RegisterInput,
  User,
} from "./types";
import type { PortalBranding } from "./portalBranding";

export type PasswordResetValidateResponse = {
  branding: PortalBranding;
  organization_handle: string;
};

export async function login(payload: LoginInput): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    if (
      response.status === 403 &&
      payload?.detail &&
      typeof payload.detail === "object" &&
      payload.detail.lock_reason === "trial_expired"
    ) {
      redirectToSubscriptionRestore(
        typeof payload.detail.subscription_state === "string" ? payload.detail.subscription_state : "Locked",
        "trial_expired",
      );
      throw new Error(
        typeof payload.detail.message === "string"
          ? payload.detail.message
          : "Your SailsPipeline demo has ended.",
      );
    }

    throw new Error(await parseApiError(response, "Login failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token, "crm");
  setLastOrganizationHandle(payload.organization_handle);
  return data;
}

export async function register(payload: RegisterInput): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Registration failed."));
  }

  return response.json();
}

export async function registerAgencyWorkspace(payload: PublicRegisterInput): Promise<AuthResponse> {
  const response = await apiFetch(`${API_BASE}/public/register`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Agency registration failed."));
  }

  const data: AuthResponse = await response.json();
  setToken(data.access_token, "crm");
  return data;
}

export async function validateResetPasswordToken(token: string): Promise<PasswordResetValidateResponse> {
  const response = await apiFetch(
    `${API_BASE}/public/auth/reset-password/validate/${encodeURIComponent(token)}`,
    { headers: authHeaders(false) },
  );

  if (!response.ok) {
    throw new Error(await parseApiError(response, "This password reset link is invalid or has expired."));
  }

  return response.json();
}

export async function requestPasswordReset(payload: ForgotPasswordInput): Promise<void> {
  const response = await apiFetch(`${API_BASE}/public/auth/forgot-password`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify({
      organization_handle: payload.organization_handle,
      email: payload.email,
    }),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to send reset email."));
  }
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  const response = await apiFetch(`${API_BASE}/public/auth/reset-password`, {
    method: "POST",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify({ token, new_password: newPassword }),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to reset password."));
  }
}

export async function fetchCurrentUser(scope: AuthScope = "crm"): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/me`, {
    headers: authHeaders(false, scope),
  });

  if (!response.ok) {
    clearToken(scope);
    throw new Error("Session expired.");
  }

  return response.json();
}

export async function updateCurrentUserSignature(emailSignatureBlock: string | null): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/me/signature`, {
    method: "PUT",
    headers: authHeaders(true, "crm"),
    body: JSON.stringify({ email_signature_block: emailSignatureBlock }),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to save email signature."));
  }

  return response.json();
}

export async function uploadCurrentUserAvatar(file: Blob, filename = "avatar.png"): Promise<{ avatar_url: string }> {
  const formData = new FormData();
  formData.append("file", file, filename);

  const response = await apiFetch(`${API_BASE}/auth/me/avatar`, {
    method: "POST",
    headers: authHeaders(false, "crm"),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload headshot."));
  }

  return response.json();
}

export async function deleteCurrentUserAvatar(): Promise<User> {
  const response = await apiFetch(`${API_BASE}/auth/me/avatar`, {
    method: "DELETE",
    headers: authHeaders(false, "crm"),
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to remove headshot."));
  }

  return response.json();
}

export async function uploadCurrentUserSignatureImage(file: File): Promise<{ image_url: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch(`${API_BASE}/auth/me/signature-image`, {
    method: "POST",
    headers: authHeaders(false, "crm"),
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await parseApiError(response, "Unable to upload signature image."));
  }

  return response.json();
}

export function logout(scope: AuthScope = "crm"): void {
  clearToken(scope);
}

export { authHeaders, getToken };