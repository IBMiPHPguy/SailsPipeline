"""Helpers for serializing UserRead with resolved agent capabilities."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User
from app.schemas import AgentCapabilitiesRead, UserRead
from app.services.agent_capability_service import get_capabilities_for_user
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


def user_to_read(db: Session, user: User) -> UserRead:
    """Build UserRead including resolved capabilities for tenant CRM users."""
    base = UserRead.model_validate(user)
    if user.role == USER_ROLE_PLATFORM_SUPER_ADMIN or user.agency_id is None:
        return base

    caps = get_capabilities_for_user(db, user)
    return base.model_copy(
        update={"capabilities": AgentCapabilitiesRead.model_validate(caps.model_dump())}
    )
