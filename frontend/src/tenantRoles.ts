export const USER_ROLE_PLATFORM_SUPER_ADMIN = "platform_super_admin";
export const USER_ROLE_TENANT_SUPER_USER = "tenant_super_user";
export const USER_ROLE_TENANT_AGENT = "tenant_agent";

export type UserRole =
  | typeof USER_ROLE_PLATFORM_SUPER_ADMIN
  | typeof USER_ROLE_TENANT_SUPER_USER
  | typeof USER_ROLE_TENANT_AGENT;

export function isTenantSuperUser(role: string | undefined): boolean {
  return role === USER_ROLE_TENANT_SUPER_USER;
}

export function isPlatformSuperAdmin(role: string | undefined): boolean {
  return role === USER_ROLE_PLATFORM_SUPER_ADMIN;
}
