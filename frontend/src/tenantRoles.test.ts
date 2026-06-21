import { describe, expect, it } from "vitest";
import {
  isPlatformSuperAdmin,
  isTenantSuperUser,
  USER_ROLE_PLATFORM_SUPER_ADMIN,
  USER_ROLE_TENANT_AGENT,
  USER_ROLE_TENANT_SUPER_USER,
} from "./tenantRoles";

describe("tenantRoles", () => {
  it("identifies tenant super users", () => {
    expect(isTenantSuperUser(USER_ROLE_TENANT_SUPER_USER)).toBe(true);
    expect(isTenantSuperUser(USER_ROLE_TENANT_AGENT)).toBe(false);
    expect(isTenantSuperUser(undefined)).toBe(false);
  });

  it("identifies platform super admins", () => {
    expect(isPlatformSuperAdmin(USER_ROLE_PLATFORM_SUPER_ADMIN)).toBe(true);
    expect(isPlatformSuperAdmin(USER_ROLE_TENANT_SUPER_USER)).toBe(false);
    expect(isPlatformSuperAdmin(undefined)).toBe(false);
  });
});
