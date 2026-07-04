from __future__ import annotations

import re
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Agency, User
from app.security import hash_password
from app.services.agency_settings_service import seed_agency_settings_for_tenant
from app.services.workflow_template_seed import seed_agency_workflow_templates
from app.services.auth_service import normalize_organization_handle
from app.services.bridge_service import (
    ORGANIZATION_HANDLE_PATTERN,
    build_username_from_full_name,
    validate_organization_handle,
)
from app.services.subscription_service import compute_trial_ends_at
from app.tenant_roles import SUBSCRIPTION_STATE_TRIALING, USER_ROLE_TENANT_SUPER_USER

PUBLIC_REGISTRATION_SUCCESS_MESSAGE = (
    "If registration is available for this email, your workspace has been created "
    "and a welcome message has been dispatched."
)


class PublicRegistrationUnavailableError(Exception):
    """Registration must not reveal whether the email is already registered."""


def _build_organization_handle_from_agency_name(db: Session, agency_name: str) -> str:
    collapsed = re.sub(r"\s+", " ", agency_name.strip())
    if not collapsed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agency name is required.")

    base = re.sub(r"[^a-z0-9]+", "-", collapsed.lower()).strip("-")
    if len(base) < 2:
        base = "agency"
    base = base[:50].rstrip("-") or "agency"

    candidate = base
    suffix = 1
    while db.query(Agency).filter(Agency.organization_handle == candidate).first():
        suffix += 1
        tail = f"-{suffix}"
        candidate = f"{base[: 50 - len(tail)]}{tail}"

    normalized = normalize_organization_handle(candidate)
    if not ORGANIZATION_HANDLE_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agency name could not produce a valid organization handle. Try a simpler name.",
        )
    return validate_organization_handle(normalized)


def register_public_tenant(
    db: Session,
    *,
    agency_name: str,
    admin_email: str,
    admin_name: str,
    password: str,
) -> tuple[User, Agency]:
    normalized_email = admin_email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is required.")

    if db.query(User).filter(User.email == normalized_email).first():
        raise PublicRegistrationUnavailableError

    agency_label = agency_name.strip()
    if not agency_label:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agency name is required.")

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    organization_handle = _build_organization_handle_from_agency_name(db, agency_label)
    username = build_username_from_full_name(db, admin_name, normalized_email)
    agency_id = str(uuid.uuid4())

    agency = Agency(
        id=agency_id,
        name=agency_label,
        slug=organization_handle,
        organization_handle=organization_handle,
        subscription_state=SUBSCRIPTION_STATE_TRIALING,
        trial_ends_at=compute_trial_ends_at(),
        is_active=True,
    )
    user = User(
        agency_id=agency_id,
        username=username,
        email=normalized_email,
        password_hash=password_hash,
        role=USER_ROLE_TENANT_SUPER_USER,
    )

    try:
        db.add(agency)
        db.flush()
        db.add(user)
        seed_agency_settings_for_tenant(db, agency_id=agency_id, agency_name=agency_label)
        seed_agency_workflow_templates(db, agency_id)
        db.commit()
        db.refresh(user)
        db.refresh(agency)
        return user, agency
    except IntegrityError:
        db.rollback()
        raise PublicRegistrationUnavailableError from None
    except Exception:
        db.rollback()
        raise
