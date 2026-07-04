from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Agency, User
from app.services.agency_settings_service import build_portal_branding_payload, get_agency_settings_row
from app.services.auth_service import resolve_agency_by_organization_handle

RESET_TOKEN_TTL = timedelta(hours=1)
FORGOT_PASSWORD_SUCCESS_MESSAGE = (
    "If the account exists, a reset link has been dispatched."
)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def find_active_tenant_user_for_password_reset(
    db: Session,
    *,
    organization_handle: str,
    email: str,
) -> User | None:
    agency = resolve_agency_by_organization_handle(db, organization_handle)
    if agency is None:
        return None

    normalized_email = email.strip().lower()
    if not normalized_email:
        return None

    return (
        db.query(User)
        .filter(
            User.agency_id == agency.id,
            User.email == normalized_email,
            User.is_active.is_(True),
        )
        .first()
    )


def issue_password_reset_token(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_reset_token(raw_token)
    user.reset_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + RESET_TOKEN_TTL
    db.add(user)
    db.commit()
    db.refresh(user)
    return raw_token


def find_user_by_valid_reset_token(db: Session, raw_token: str) -> User | None:
    token_hash = hash_reset_token(raw_token.strip())
    now = datetime.now(UTC).replace(tzinfo=None)
    return (
        db.query(User)
        .filter(
            User.reset_token_hash == token_hash,
            User.reset_token_expires_at.isnot(None),
            User.reset_token_expires_at > now,
            User.is_active.is_(True),
        )
        .first()
    )


def clear_password_reset_token(db: Session, user: User) -> None:
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()


def reset_user_password(db: Session, user: User, new_password_hash: str) -> None:
    user.password_hash = new_password_hash
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.add(user)
    db.commit()


def get_password_reset_portal_context(db: Session, raw_token: str) -> dict:
    user = assert_valid_reset_token(db, raw_token)
    if not user.agency_id:
        from app.services.welcome_email_service import load_system_welcome_branding

        system = load_system_welcome_branding()
        branding = {
            "agency_name": system.agency_name,
            "brand_logo_url": system.brand_logo_url,
            "primary_color": system.primary_color,
            "secondary_color": system.secondary_color,
            "business_address": None,
            "business_phone": None,
        }
        return {"branding": branding, "organization_handle": ""}

    row = get_agency_settings_row(db, agency_id=user.agency_id)
    agency = user.agency if user.agency is not None else db.get(Agency, user.agency_id)
    return {
        "branding": build_portal_branding_payload(row),
        "organization_handle": agency.organization_handle if agency is not None else "",
    }


def assert_valid_reset_token(db: Session, raw_token: str) -> User:
    user = find_user_by_valid_reset_token(db, raw_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is invalid or has expired.",
        )
    return user
