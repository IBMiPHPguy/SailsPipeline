export type AuthScope = "crm" | "bridge";

const CRM_TOKEN_KEY = "sailspipeline_crm_token";
const BRIDGE_TOKEN_KEY = "sailspipeline_bridge_token";
const LEGACY_TOKEN_KEY = "sailspipeline_token";
const LEGACY_CRUISE_TOKEN_KEY = "cruisetravelnow_token";

function tokenKeyForScope(scope: AuthScope): string {
  return scope === "bridge" ? BRIDGE_TOKEN_KEY : CRM_TOKEN_KEY;
}

function migrateLegacyCrmToken(): string | null {
  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (legacy) {
    localStorage.setItem(CRM_TOKEN_KEY, legacy);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    return legacy;
  }

  const cruiseLegacy = localStorage.getItem(LEGACY_CRUISE_TOKEN_KEY);
  if (cruiseLegacy) {
    localStorage.setItem(CRM_TOKEN_KEY, cruiseLegacy);
    localStorage.removeItem(LEGACY_CRUISE_TOKEN_KEY);
    return cruiseLegacy;
  }

  return null;
}

export function getToken(scope: AuthScope = "crm"): string | null {
  const scoped = localStorage.getItem(tokenKeyForScope(scope));
  if (scoped) {
    return scoped;
  }

  if (scope === "crm") {
    return migrateLegacyCrmToken();
  }

  return null;
}

export function setToken(token: string, scope: AuthScope = "crm"): void {
  localStorage.setItem(tokenKeyForScope(scope), token);
  if (scope === "crm") {
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    localStorage.removeItem(LEGACY_CRUISE_TOKEN_KEY);
  }
}

export function clearToken(scope: AuthScope = "crm"): void {
  localStorage.removeItem(tokenKeyForScope(scope));
  if (scope === "crm") {
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    localStorage.removeItem(LEGACY_CRUISE_TOKEN_KEY);
  }
}

export function validatePassword(password: string): string | null {
  if (password.includes(" ")) {
    return "Password cannot contain spaces.";
  }
  if (password.length <= 10) {
    return "Password must be more than 10 characters.";
  }
  if (!/[a-z]/.test(password)) {
    return "Password must include at least one lowercase letter.";
  }
  if (!/[A-Z]/.test(password)) {
    return "Password must include at least one uppercase letter.";
  }
  if (!/\d/.test(password)) {
    return "Password must include at least one numeral.";
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return "Password must include at least one special character.";
  }
  return null;
}
