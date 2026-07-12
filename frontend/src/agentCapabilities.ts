import { isTenantSuperUser } from "./tenantRoles";
import type { User } from "./types";

export type CapabilityGatedView =
  | "marketing-campaigns"
  | "workflows"
  | "group-blocks"
  | "agency-settings"
  | "team";

export function canAccessCapabilityView(user: User, view: CapabilityGatedView): boolean {
  const caps = user.capabilities;

  if (caps) {
    if (caps.is_unrestricted) {
      return true;
    }
    switch (view) {
      case "marketing-campaigns":
        return caps.show_marketing_campaigns_tab || isTenantSuperUser(user.role);
      case "workflows":
        return caps.show_workflows_tab;
      case "group-blocks":
        return caps.show_group_blocks_tab;
      case "agency-settings":
        return caps.show_agency_settings_tab;
      case "team":
        return caps.show_team_tab;
      default:
        return false;
    }
  }

  // Fallback when capabilities are missing: preserve prior super-user access;
  // agents cannot open marketing/workflows/groups/settings/team.
  return isTenantSuperUser(user.role);
}

export function shouldSkipGroupIntakePrompt(user: User | null | undefined): boolean {
  if (!user) {
    return false;
  }
  if (isTenantSuperUser(user.role)) {
    return false;
  }
  const caps = user.capabilities;
  // Safe agent default when capabilities are missing: individual requests only.
  if (!caps) {
    return true;
  }
  return caps.skip_group_intake_prompt && !caps.is_unrestricted;
}

export function canCreateGroupBlocks(user: User): boolean {
  const caps = user.capabilities;
  if (!caps) {
    return isTenantSuperUser(user.role);
  }
  return caps.is_unrestricted || caps.create_own_groups;
}

export function canMutateGroupBlock(
  user: User,
  group: { created_by_id?: number | null },
): boolean {
  const caps = user.capabilities;
  if (!caps) {
    return isTenantSuperUser(user.role);
  }
  if (caps.is_unrestricted) {
    return true;
  }

  const isOwnGroup = group.created_by_id != null && group.created_by_id === user.id;
  if (isOwnGroup) {
    return caps.create_own_groups;
  }

  if (caps.manage_other_agent_groups) {
    return true;
  }

  // other_agent_groups_read_only, or no manage_other without unrestricted
  return false;
}

export function canManageTravelRequest(
  user: User,
  request: { created_by?: { id: number } | null },
): boolean {
  const caps = user.capabilities;
  if (!caps) {
    return isTenantSuperUser(user.role);
  }
  if (caps.is_unrestricted || caps.manage_other_agent_requests) {
    return true;
  }
  return request.created_by?.id === user.id;
}
