from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Agency, PlatformInvitation, User
from app.security import hash_password
from app.services.auth_service import normalize_organization_handle
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_SUPER_USER

ORGANIZATION_HANDLE_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$")
USERNAME_PATTERN = re.compile(r"^\S{3,80}$")


def validate_organization_handle(handle: str) -> str:
    normalized = normalize_organization_handle(handle)
    if not ORGANIZATION_HANDLE_PATTERN.fullmatch(normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization handle must be 2–50 lowercase letters, numbers, or hyphens.",
        )
    return normalized


def invitation_token_status(invitation: PlatformInvitation, *, now: datetime | None = None) -> str:
    if invitation.is_used:
        return "Used"
    if invitation.cancelled_at is not None:
        return "Cancelled"
    current = now or datetime.now(UTC).replace(tzinfo=None)
    expires_at = invitation.expires_at
    if expires_at.tzinfo is not None:
        expires_at = expires_at.replace(tzinfo=None)
    if expires_at < current:
        return "Expired"
    return "Pending"


def get_valid_platform_invitation(db: Session, token: str) -> PlatformInvitation:
    invitation = db.query(PlatformInvitation).filter(PlatformInvitation.token == token).first()
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    if invitation.is_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been used.")
    if invitation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has been revoked.")
    if invitation_token_status(invitation) == "Expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired.")
    return invitation


def _assert_handle_available_for_invite(db: Session, organization_handle: str) -> PlatformInvitation | None:
    if db.query(Agency).filter(Agency.organization_handle == organization_handle).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization handle is already assigned to an active agency.",
        )

    existing_invite = (
        db.query(PlatformInvitation)
        .filter(PlatformInvitation.target_organization_handle == organization_handle)
        .first()
    )
    if existing_invite is None:
        return None

    if existing_invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization handle was already provisioned from a prior invitation.",
        )

    if invitation_token_status(existing_invite) == "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this organization handle.",
        )

    return existing_invite


def create_platform_invitation(
    db: Session,
    *,
    target_agency_name: str,
    target_organization_handle: str,
    invite_email: str,
) -> PlatformInvitation:
    agency_name = target_agency_name.strip()
    if not agency_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agency name is required.")

    organization_handle = validate_organization_handle(target_organization_handle)
    normalized_email = invite_email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner email is required.")

    reusable_invite = _assert_handle_available_for_invite(db, organization_handle)
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=settings.platform_invite_expire_days)
    token = secrets.token_urlsafe(48)

    if reusable_invite is not None:
        reusable_invite.target_agency_name = agency_name
        reusable_invite.invite_email = normalized_email
        reusable_invite.token = token
        reusable_invite.is_used = False
        reusable_invite.cancelled_at = None
        reusable_invite.expires_at = expires_at
        db.commit()
        db.refresh(reusable_invite)
        return reusable_invite

    invitation = PlatformInvitation(
        id=str(uuid.uuid4()),
        target_agency_name=agency_name,
        target_organization_handle=organization_handle,
        invite_email=normalized_email,
        token=token,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def get_bridge_summary(db: Session) -> dict:
    agencies = db.query(Agency).order_by(Agency.created_at.desc()).all()
    invitations = db.query(PlatformInvitation).order_by(PlatformInvitation.expires_at.desc()).all()
    return {
        "agencies": agencies,
        "invitations": invitations,
    }


def get_agency_for_bridge(db: Session, agency_id: str) -> Agency:
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    return agency


def get_bridge_tenant_detail(db: Session, agency_id: str) -> dict:
    agency = get_agency_for_bridge(db, agency_id)
    users = (
        db.query(User)
        .filter(User.agency_id == agency.id)
        .order_by(User.role.asc(), User.username.asc())
        .all()
    )
    return {"agency": agency, "users": users}


def _assert_handle_available_for_agency(db: Session, organization_handle: str, *, agency_id: str) -> None:
    existing = (
        db.query(Agency)
        .filter(
            Agency.organization_handle == organization_handle,
            Agency.id != agency_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization handle is already assigned to another agency.",
        )


def update_bridge_tenant(
    db: Session,
    agency_id: str,
    *,
    name: str,
    organization_handle: str,
    subscription_state: str,
) -> Agency:
    from app.tenant_roles import SUBSCRIPTION_STATES

    agency = get_agency_for_bridge(db, agency_id)
    agency_name = name.strip()
    if not agency_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agency name is required.")

    normalized_handle = validate_organization_handle(organization_handle)
    if subscription_state not in SUBSCRIPTION_STATES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subscription state.")

    _assert_handle_available_for_agency(db, normalized_handle, agency_id=agency.id)

    agency.name = agency_name
    agency.organization_handle = normalized_handle
    agency.slug = normalized_handle
    agency.subscription_state = subscription_state
    db.commit()
    db.refresh(agency)
    return agency


def cancel_platform_invitation(db: Session, invitation_id: str) -> PlatformInvitation:
    invitation = db.get(PlatformInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    if invitation.is_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been used.")
    if invitation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been revoked.")
    if invitation_token_status(invitation) == "Expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired.")

    invitation.cancelled_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(invitation)
    return invitation


def build_username_from_full_name(db: Session, full_name: str, email: str) -> str:
    collapsed = re.sub(r"\s+", " ", full_name.strip())
    if not collapsed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name is required.")

    parts = collapsed.split(" ")
    if len(parts) >= 2:
        candidate = f"{parts[0].lower()}.{parts[-1].lower()}"
    else:
        candidate = collapsed.lower().replace(" ", "")

    candidate = re.sub(r"[^a-z0-9._-]", "", candidate)
    if len(candidate) < 3:
        candidate = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())

    if len(candidate) < 3:
        candidate = "owner"

    candidate = candidate[:80]
    if not USERNAME_PATTERN.fullmatch(candidate):
        candidate = re.sub(r"[^a-z0-9._-]", "", email.split("@")[0].lower())[:80] or "owner"

    base = candidate
    suffix = 1
    while db.query(User).filter(User.username == candidate).first():
        suffix += 1
        tail = f"-{suffix}"
        candidate = f"{base[: 80 - len(tail)]}{tail}"

    return candidate


def accept_platform_invitation(
    db: Session,
    *,
    token: str,
    full_name: str,
    password: str,
) -> User:
    invitation = get_valid_platform_invitation(db, token)
    organization_handle = invitation.target_organization_handle

    if db.query(Agency).filter(Agency.organization_handle == organization_handle).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This organization has already been provisioned.",
        )

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    username = build_username_from_full_name(db, full_name, invitation.invite_email)
    agency_id = str(uuid.uuid4())

    agency = Agency(
        id=agency_id,
        name=invitation.target_agency_name,
        slug=organization_handle,
        organization_handle=organization_handle,
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    user = User(
        agency_id=agency_id,
        username=username,
        email=invitation.invite_email,
        password_hash=password_hash,
        role=USER_ROLE_TENANT_SUPER_USER,
    )

    try:
        db.add(agency)
        db.flush()
        db.add(user)
        invitation.is_used = True
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise
