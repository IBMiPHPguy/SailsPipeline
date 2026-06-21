from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Agency, AgencyInvitation, User
from app.security import hash_password
from app.services.bridge_service import build_username_from_full_name
from app.tenant_roles import (
    DEFAULT_INVITATION_ROLE,
    SUBSCRIPTION_STATE_LOCKED,
    SUBSCRIPTION_STATE_PAST_DUE,
    USER_ROLE_TENANT_AGENT,
    USER_ROLE_TENANT_SUPER_USER,
    USER_ROLES,
)

TENANT_ASSIGNABLE_ROLES = (USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER)


def agency_invitation_token_status(invitation: AgencyInvitation, *, now: datetime | None = None) -> str:
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


def _assert_agency_can_operate(agency: Agency) -> None:
    if agency.subscription_state in {SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_PAST_DUE}:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Subscription payment required before managing team members.",
        )


def get_valid_agency_invitation(db: Session, token: str) -> AgencyInvitation:
    invitation = db.query(AgencyInvitation).filter(AgencyInvitation.token == token).first()
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    if invitation.is_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been used.")
    if invitation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has been revoked.")
    if agency_invitation_token_status(invitation) == "Expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired.")
    return invitation


def _assert_email_available_for_agency(
    db: Session,
    agency_id: str,
    invite_email: str,
    *,
    exclude_invitation_id: str | None = None,
) -> None:
    normalized_email = invite_email.strip().lower()
    existing_user = (
        db.query(User)
        .filter(
            User.agency_id == agency_id,
            User.email == normalized_email,
        )
        .first()
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already belongs to your agency.",
        )

    pending_query = db.query(AgencyInvitation).filter(
        AgencyInvitation.agency_id == agency_id,
        AgencyInvitation.invite_email == normalized_email,
        AgencyInvitation.is_used.is_(False),
    )
    if exclude_invitation_id is not None:
        pending_query = pending_query.filter(AgencyInvitation.id != exclude_invitation_id)

    pending_invite = pending_query.first()
    if pending_invite is not None and agency_invitation_token_status(pending_invite) == "Pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this email address.",
        )


def create_agency_invitation(
    db: Session,
    *,
    agency_id: str,
    invite_email: str,
    role: str = DEFAULT_INVITATION_ROLE,
) -> AgencyInvitation:
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")

    _assert_agency_can_operate(agency)

    if role not in TENANT_ASSIGNABLE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid invitation role.")

    normalized_email = invite_email.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite email is required.")

    _assert_email_available_for_agency(db, agency_id, normalized_email)

    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=settings.agency_invite_expire_days)
    token = secrets.token_urlsafe(48)
    invitation = AgencyInvitation(
        id=str(uuid.uuid4()),
        agency_id=agency_id,
        invite_email=normalized_email,
        token=token,
        role=role,
        is_used=False,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


def get_agency_team(db: Session, agency_id: str) -> dict:
    users = (
        db.query(User)
        .filter(User.agency_id == agency_id)
        .order_by(User.role.asc(), User.username.asc())
        .all()
    )
    invitations = (
        db.query(AgencyInvitation)
        .filter(
            AgencyInvitation.agency_id == agency_id,
            AgencyInvitation.is_used.is_(False),
        )
        .order_by(AgencyInvitation.expires_at.desc())
        .all()
    )
    return {"users": users, "invitations": invitations}


def update_agency_user(
    db: Session,
    *,
    agency_id: str,
    user_id: int,
    acting_user_id: int,
    role: str | None = None,
    is_active: bool | None = None,
    email: str | None = None,
) -> User:
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.agency_id == agency_id,
        )
        .first()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if role is not None and role not in USER_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
    if role is not None and role not in TENANT_ASSIGNABLE_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role for agency user.")

    if user.id == acting_user_id:
        if role is not None and role != user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role.",
            )
        if is_active is not None and not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account.",
            )

    if email is not None:
        normalized_email = email.strip().lower()
        duplicate = (
            db.query(User)
            .filter(
                User.agency_id == agency_id,
                User.email == normalized_email,
                User.id != user.id,
            )
            .first()
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another user in your agency already uses this email address.",
            )
        user.email = normalized_email

    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active

    db.commit()
    db.refresh(user)
    return user


def accept_agency_invitation(
    db: Session,
    *,
    token: str,
    full_name: str,
    password: str,
) -> User:
    invitation = get_valid_agency_invitation(db, token)
    agency = db.get(Agency, invitation.agency_id)
    if agency is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")

    if agency.subscription_state in {SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_PAST_DUE}:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This agency subscription must be restored before joining the team.",
        )

    _assert_email_available_for_agency(
        db,
        invitation.agency_id,
        invitation.invite_email,
        exclude_invitation_id=invitation.id,
    )

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    username = build_username_from_full_name(db, full_name, invitation.invite_email)
    user = User(
        agency_id=invitation.agency_id,
        username=username,
        email=invitation.invite_email,
        password_hash=password_hash,
        role=invitation.role,
    )

    try:
        db.add(user)
        invitation.is_used = True
        db.commit()
        db.refresh(user)
        return user
    except Exception:
        db.rollback()
        raise


def cancel_agency_invitation(db: Session, *, agency_id: str, invitation_id: str) -> AgencyInvitation:
    invitation = (
        db.query(AgencyInvitation)
        .filter(
            AgencyInvitation.id == invitation_id,
            AgencyInvitation.agency_id == agency_id,
        )
        .first()
    )
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")
    if invitation.is_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been used.")
    if invitation.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has already been revoked.")
    if agency_invitation_token_status(invitation) == "Expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation has expired.")

    invitation.cancelled_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(invitation)
    return invitation
