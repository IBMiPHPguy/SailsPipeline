const TOKEN_KEY = "sailspipeline_token";
const LEGACY_TOKEN_KEY = "cruisetravelnow_token";

export function getToken(): string | null {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    return token;
  }

  const legacy = localStorage.getItem(LEGACY_TOKEN_KEY);
  if (legacy) {
    localStorage.setItem(TOKEN_KEY, legacy);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
    return legacy;
  }

  return null;
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
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
