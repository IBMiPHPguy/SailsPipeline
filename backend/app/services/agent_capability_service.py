"""Load and enforce agency agent capabilities against requests and groups."""

from __future__ import annotations

from typing import Any, Mapping

from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from app.agent_capabilities import (
    AgentCapabilities,
    AgentConfigurablePermissions,
    normalize_configurable_permissions,
    resolve_agent_capabilities,
    validate_configurable_permissions_payload,
)
from app.models import AgencyGroup, AgencySettings, TravelRequest, User
from app.services.agency_settings_service import get_agency_settings_row
from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER


def _agency_permissions_raw(settings: AgencySettings | None) -> dict[str, Any] | None:
    if settings is None:
        return None
    raw = settings.agent_permissions
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    return None


def get_capabilities_for_user(db: Session, user: User) -> AgentCapabilities:
    """Resolve capabilities for a CRM user from agency settings (+ future overrides)."""
    if user.role == USER_ROLE_TENANT_SUPER_USER:
        return resolve_agent_capabilities(role=user.role)

    agency_raw: Mapping[str, Any] | None = None
    if user.agency_id is not None:
        settings = db.get(AgencySettings, user.agency_id)
        agency_raw = _agency_permissions_raw(settings)

    # Future: load user.permission_overrides here and pass as user_overrides.
    return resolve_agent_capabilities(
        role=user.role,
        agency_permissions=agency_raw,
        user_overrides=None,
    )


def get_configurable_permissions_for_agency(
    db: Session, *, agency_id: str
) -> AgentConfigurablePermissions:
    settings = get_agency_settings_row(db, agency_id=agency_id)
    return normalize_configurable_permissions(_agency_permissions_raw(settings))


def save_configurable_permissions(
    db: Session,
    *,
    agency_id: str,
    permissions: Mapping[str, Any] | AgentConfigurablePermissions,
) -> AgentConfigurablePermissions:
    if isinstance(permissions, AgentConfigurablePermissions):
        normalized = normalize_configurable_permissions(permissions.model_dump())
    else:
        try:
            normalized = validate_configurable_permissions_payload(permissions)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    settings = get_agency_settings_row(db, agency_id=agency_id)
    settings.agent_permissions = normalized.model_dump()
    db.commit()
    db.refresh(settings)
    return normalized


def is_request_owner(user: User, request: TravelRequest) -> bool:
    return request.created_by_id == user.id


def can_view_request(user: User, request: TravelRequest, caps: AgentCapabilities) -> bool:
    if caps.is_unrestricted or caps.view_other_agent_requests:
        return True
    return is_request_owner(user, request)


def can_manage_request(user: User, request: TravelRequest, caps: AgentCapabilities) -> bool:
    if caps.is_unrestricted or caps.manage_other_agent_requests:
        return True
    return is_request_owner(user, request)


def assert_can_view_request(user: User, request: TravelRequest, caps: AgentCapabilities) -> None:
    if not can_view_request(user, request, caps):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this request.",
        )


def assert_can_manage_request(user: User, request: TravelRequest, caps: AgentCapabilities) -> None:
    if not can_manage_request(user, request, caps):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this request.",
        )


def filter_requests_query_for_user(
    query: Query,
    user: User,
    caps: AgentCapabilities,
) -> Query:
    """Restrict a TravelRequest query to rows the user may view."""
    if caps.is_unrestricted or caps.view_other_agent_requests:
        return query
    return query.filter(TravelRequest.created_by_id == user.id)


def filter_requests_to_owned_only(
    query: Query,
    user: User,
    *,
    own_only: bool,
) -> Query:
    if not own_only:
        return query
    return query.filter(TravelRequest.created_by_id == user.id)


def is_group_owner(user: User, group: AgencyGroup) -> bool:
    return group.created_by_id is not None and group.created_by_id == user.id


def can_view_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> bool:
    if caps.is_unrestricted:
        return True
    if is_group_owner(user, group):
        return caps.create_own_groups or caps.manage_other_agent_groups or caps.book_other_agent_groups
    if caps.manage_other_agent_groups or caps.book_other_agent_groups:
        return True
    return False


def can_mutate_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> bool:
    if caps.is_unrestricted:
        return True
    if is_group_owner(user, group):
        return caps.create_own_groups
    return caps.manage_other_agent_groups


def can_book_into_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> bool:
    if caps.is_unrestricted:
        return True
    if is_group_owner(user, group):
        return caps.create_own_groups or caps.book_other_agent_groups
    return caps.book_other_agent_groups


def assert_can_view_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> None:
    if not can_view_group(user, group, caps):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this group.",
        )


def assert_can_mutate_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> None:
    if not can_mutate_group(user, group, caps):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this group.",
        )


def assert_can_book_into_group(user: User, group: AgencyGroup, caps: AgentCapabilities) -> None:
    if not can_book_into_group(user, group, caps):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to book into this group.",
        )


def assert_can_create_groups(caps: AgentCapabilities) -> None:
    if not (caps.is_unrestricted or caps.create_own_groups):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create groups.",
        )


def assert_can_access_group_blocks_page(caps: AgentCapabilities) -> None:
    if not (caps.is_unrestricted or caps.show_group_blocks_tab):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage group blocks.",
        )


def assert_can_manage_marketing_campaigns(caps: AgentCapabilities) -> None:
    if not caps.can_manage_marketing_campaigns:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage marketing campaigns.",
        )


def group_visibility_filter(user: User, caps: AgentCapabilities):
    """SQLAlchemy filter for groups the user may see on the Group Blocks list."""
    from sqlalchemy import or_

    if caps.is_unrestricted or caps.manage_other_agent_groups:
        return True  # no extra filter
    if caps.create_own_groups and caps.book_other_agent_groups:
        return True  # own + others (read-only for others)
    if caps.create_own_groups:
        return AgencyGroup.created_by_id == user.id
    if caps.book_other_agent_groups:
        # Book-other alone: no Group Blocks tab, but if listing somehow, show others.
        return or_(AgencyGroup.created_by_id != user.id, AgencyGroup.created_by_id.is_(None))
    return AgencyGroup.created_by_id == user.id  # effectively none if no create


def picker_visibility_filter(user: User, caps: AgentCapabilities):
    """SQLAlchemy filter for groups available in the booking picker."""
    from sqlalchemy import or_

    if caps.is_unrestricted:
        return True
    clauses = []
    if caps.create_own_groups:
        clauses.append(AgencyGroup.created_by_id == user.id)
    if caps.book_other_agent_groups:
        clauses.append(
            or_(AgencyGroup.created_by_id != user.id, AgencyGroup.created_by_id.is_(None))
        )
    if not clauses:
        return False  # no groups
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)
