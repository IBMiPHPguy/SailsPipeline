"""Unit tests for agency agent capability resolution (no DB)."""

from app.agent_capabilities import (
    normalize_configurable_permissions,
    resolve_agent_capabilities,
    validate_configurable_permissions_payload,
)
from app.tenant_roles import USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER


def test_agent_defaults_are_locked_down():
    caps = resolve_agent_capabilities(role=USER_ROLE_TENANT_AGENT)
    assert caps.view_other_agent_requests is False
    assert caps.manage_other_agent_requests is False
    assert caps.create_own_groups is False
    assert caps.manage_other_agent_groups is False
    assert caps.book_other_agent_groups is False
    assert caps.sales_analytics_own_only is True
    assert caps.reports_own_only is True
    assert caps.show_marketing_campaigns_tab is False
    assert caps.show_workflows_tab is False
    assert caps.show_agency_settings_tab is False
    assert caps.show_team_tab is False
    assert caps.clients_full_access is True
    assert caps.show_group_blocks_tab is False
    assert caps.skip_group_intake_prompt is True
    assert caps.can_manage_marketing_campaigns is False
    assert caps.is_unrestricted is False


def test_super_user_is_unrestricted():
    caps = resolve_agent_capabilities(role=USER_ROLE_TENANT_SUPER_USER)
    assert caps.is_unrestricted is True
    assert caps.show_group_blocks_tab is True
    assert caps.skip_group_intake_prompt is False
    assert caps.sales_analytics_own_only is False
    assert caps.can_manage_marketing_campaigns is True


def test_manage_other_requests_forces_view():
    normalized = normalize_configurable_permissions(
        {"manage_other_agent_requests": True, "view_other_agent_requests": False}
    )
    assert normalized.view_other_agent_requests is True
    assert normalized.manage_other_agent_requests is True


def test_manage_other_groups_requires_create_own():
    normalized = normalize_configurable_permissions(
        {"manage_other_agent_groups": True, "create_own_groups": False}
    )
    assert normalized.create_own_groups is False
    assert normalized.manage_other_agent_groups is False


def test_agency_json_enables_group_tab_and_prompt():
    caps = resolve_agent_capabilities(
        role=USER_ROLE_TENANT_AGENT,
        agency_permissions={"create_own_groups": True},
    )
    assert caps.show_group_blocks_tab is True
    assert caps.skip_group_intake_prompt is False
    assert caps.create_own_groups is True


def test_book_other_without_create_skips_tab_but_not_prompt():
    caps = resolve_agent_capabilities(
        role=USER_ROLE_TENANT_AGENT,
        agency_permissions={"book_other_agent_groups": True},
    )
    assert caps.show_group_blocks_tab is False
    assert caps.skip_group_intake_prompt is False
    assert caps.other_agent_groups_read_only is True


def test_user_overrides_merge_after_agency():
    caps = resolve_agent_capabilities(
        role=USER_ROLE_TENANT_AGENT,
        agency_permissions={"view_other_agent_requests": False},
        user_overrides={"view_other_agent_requests": True},
    )
    assert caps.view_other_agent_requests is True


def test_unknown_permission_key_rejected():
    try:
        validate_configurable_permissions_payload({"not_a_real_key": True})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unknown agent permission keys" in str(exc)
