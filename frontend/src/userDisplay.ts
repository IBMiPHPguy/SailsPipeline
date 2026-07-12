/** Display helpers mirroring backend/app/user_display.py */

export function splitUsernameParts(username: string): string[] {
  const raw = (username || "").trim();
  if (!raw) {
    return [];
  }
  return raw.split(/[._\-]+/).filter(Boolean);
}

function titleCasePart(part: string): string {
  const lowered = part.toLowerCase();
  return lowered ? lowered[0].toUpperCase() + lowered.slice(1) : "";
}

export function formatUsernameDisplayName(username: string): string {
  const parts = splitUsernameParts(username);
  if (parts.length === 0) {
    const raw = (username || "").trim();
    return raw ? raw[0].toUpperCase() + raw.slice(1).toLowerCase() : "";
  }
  return parts.map(titleCasePart).join(" ");
}

export function usernameFirstLast(username: string): { firstName: string; lastName: string } {
  const parts = splitUsernameParts(username);
  if (parts.length === 0) {
    return { firstName: "", lastName: "" };
  }
  if (parts.length === 1) {
    return { firstName: titleCasePart(parts[0]), lastName: "" };
  }
  return {
    firstName: titleCasePart(parts[0]),
    lastName: titleCasePart(parts[parts.length - 1]),
  };
}

export function initialsFromUsername(username: string): string {
  const { firstName, lastName } = usernameFirstLast(username);
  if (firstName && lastName) {
    return `${firstName[0]}${lastName[0]}`.toUpperCase();
  }
  if (firstName) {
    return firstName.slice(0, 2).toUpperCase();
  }
  return "?";
}

export function formatRoleLabel(role: string): string {
  if (role === "tenant_super_user") {
    return "Super user";
  }
  if (role === "tenant_agent") {
    return "Agent";
  }
  if (role === "platform_super_admin") {
    return "Platform admin";
  }
  return role;
}
