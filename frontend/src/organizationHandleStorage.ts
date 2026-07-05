const ORGANIZATION_HANDLE_COOKIE = "sailspipeline_org_handle";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  const parts = document.cookie.split(";").map((part) => part.trim());
  for (const part of parts) {
    if (part.startsWith(prefix)) {
      return decodeURIComponent(part.slice(prefix.length));
    }
  }
  return null;
}

export function getLastOrganizationHandle(): string | null {
  const value = readCookie(ORGANIZATION_HANDLE_COOKIE)?.trim();
  return value || null;
}

export function setLastOrganizationHandle(handle: string): void {
  const normalized = handle.trim();
  if (!normalized) {
    return;
  }

  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${ORGANIZATION_HANDLE_COOKIE}=${encodeURIComponent(normalized)}; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}; SameSite=Lax${secure}`;
}
