"""Agency agent capability registry and resolution.

Merge order (future-proof):
  registry defaults → agency_settings.agent_permissions JSON → optional per-user overrides

Per-user overrides are accepted by the resolver but not persisted yet.
Hard-coded agent tab/scoping flags live here so they can become toggles later
without changing call sites.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER

# Configurable agency-wide toggles (admin-editable).
CONFIGURABLE_PERMISSION_KEYS = (
    "view_other_agent_requests",
    "manage_other_agent_requests",
    "create_own_groups",
    "manage_other_agent_groups",
    "book_other_agent_groups",
)

DEFAULT_CONFIGURABLE_PERMISSIONS: dict[str, bool] = {
    "view_other_agent_requests": False,
    "manage_other_agent_requests": False,
    "create_own_groups": False,
    "manage_other_agent_groups": False,
    "book_other_agent_groups": False,
}


class AgentConfigurablePermissions(BaseModel):
    """Agency-wide toggles stored on agency_settings.agent_permissions."""

    model_config = ConfigDict(extra="ignore")

    view_other_agent_requests: bool = False
    manage_other_agent_requests: bool = False
    create_own_groups: bool = False
    manage_other_agent_groups: bool = False
    book_other_agent_groups: bool = False


class AgentCapabilities(BaseModel):
    """Fully resolved capabilities for a CRM user (UI + API share this DTO)."""

    model_config = ConfigDict(extra="ignore")

    # Configurable (agency-wide today; per-agent overrides later).
    view_other_agent_requests: bool = False
    manage_other_agent_requests: bool = False
    create_own_groups: bool = False
    manage_other_agent_groups: bool = False
    book_other_agent_groups: bool = False

    # Derived / hard-coded for agents (architected as fields for future toggles).
    sales_analytics_own_only: bool = True
    reports_own_only: bool = True
    show_marketing_campaigns_tab: bool = False
    show_workflows_tab: bool = False
    show_agency_settings_tab: bool = False
    show_team_tab: bool = False
    clients_full_access: bool = True
    show_group_blocks_tab: bool = False
    skip_group_intake_prompt: bool = True
    other_agent_groups_read_only: bool = False
    can_manage_marketing_campaigns: bool = False
    is_unrestricted: bool = False


def normalize_configurable_permissions(
    raw: Mapping[str, Any] | None,
) -> AgentConfigurablePermissions:
    """Merge raw JSON with defaults and enforce dependency rules."""
    base = dict(DEFAULT_CONFIGURABLE_PERMISSIONS)
    if raw:
        for key in CONFIGURABLE_PERMISSION_KEYS:
            if key in raw:
                base[key] = bool(raw[key])

    if base["manage_other_agent_requests"]:
        base["view_other_agent_requests"] = True
    if not base["create_own_groups"]:
        base["manage_other_agent_groups"] = False

    return AgentConfigurablePermissions.model_validate(base)


def validate_configurable_permissions_payload(
    raw: Mapping[str, Any] | None,
) -> AgentConfigurablePermissions:
    """Validate an admin update payload (same rules as normalize)."""
    if raw is None:
        return AgentConfigurablePermissions()
    unknown = set(raw.keys()) - set(CONFIGURABLE_PERMISSION_KEYS)
    if unknown:
        raise ValueError(f"Unknown agent permission keys: {', '.join(sorted(unknown))}")
    return normalize_configurable_permissions(raw)


def _super_user_capabilities() -> AgentCapabilities:
    return AgentCapabilities(
        view_other_agent_requests=True,
        manage_other_agent_requests=True,
        create_own_groups=True,
        manage_other_agent_groups=True,
        book_other_agent_groups=True,
        sales_analytics_own_only=False,
        reports_own_only=False,
        show_marketing_campaigns_tab=True,
        show_workflows_tab=True,
        show_agency_settings_tab=True,
        show_team_tab=True,
        clients_full_access=True,
        show_group_blocks_tab=True,
        skip_group_intake_prompt=False,
        other_agent_groups_read_only=False,
        can_manage_marketing_campaigns=True,
        is_unrestricted=True,
    )


def resolve_agent_capabilities(
    *,
    role: str,
    agency_permissions: Mapping[str, Any] | None = None,
    user_overrides: Mapping[str, Any] | None = None,
) -> AgentCapabilities:
    """Resolve effective capabilities for a user.

    Merge order: defaults → agency JSON → user overrides (future).
    """
    if role == USER_ROLE_TENANT_SUPER_USER:
        return _super_user_capabilities()

    configurable = normalize_configurable_permissions(agency_permissions)
    if user_overrides:
        merged = configurable.model_dump()
        for key in CONFIGURABLE_PERMISSION_KEYS:
            if key in user_overrides:
                merged[key] = bool(user_overrides[key])
        configurable = normalize_configurable_permissions(merged)

    create_own = configurable.create_own_groups
    manage_other_groups = configurable.manage_other_agent_groups
    book_other = configurable.book_other_agent_groups

    return AgentCapabilities(
        view_other_agent_requests=configurable.view_other_agent_requests,
        manage_other_agent_requests=configurable.manage_other_agent_requests,
        create_own_groups=create_own,
        manage_other_agent_groups=manage_other_groups,
        book_other_agent_groups=book_other,
        sales_analytics_own_only=True,
        reports_own_only=True,
        show_marketing_campaigns_tab=False,
        show_workflows_tab=False,
        show_agency_settings_tab=False,
        show_team_tab=False,
        clients_full_access=True,
        show_group_blocks_tab=create_own or manage_other_groups,
        skip_group_intake_prompt=not create_own and not book_other,
        other_agent_groups_read_only=book_other and not manage_other_groups,
        can_manage_marketing_campaigns=False,
        is_unrestricted=False,
    )
