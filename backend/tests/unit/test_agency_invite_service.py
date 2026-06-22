import pytest
from datetime import UTC, datetime, timedelta
from fastapi import HTTPException

from app.models import Agency, AgencyInvitation, User
from app.security import hash_password
from app.services.agency_invite_service import (
    accept_agency_invitation,
    agency_invitation_token_status,
    cancel_agency_invitation,
    create_agency_invitation,
    get_valid_agency_invitation,
    update_agency_user,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import (
    SUBSCRIPTION_STATE_LOCKED,
    USER_ROLE_TENANT_AGENT,
    USER_ROLE_TENANT_SUPER_USER,
)


@pytest.mark.unit
def test_create_agency_invitation_returns_token(db, test_user):
    invitation = create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="agent@example.com",
        role=USER_ROLE_TENANT_AGENT,
    )
    assert invitation.agency_id == DEFAULT_AGENCY_ID
    assert invitation.invite_email == "agent@example.com"
    assert invitation.is_used is False
    assert agency_invitation_token_status(invitation) == "Pending"


@pytest.mark.unit
def test_create_agency_invitation_expires_in_three_days(db, test_user):
    from app.config import settings

    before = datetime.now(UTC).replace(tzinfo=None)
    invitation = create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="short-lived@example.com",
    )
    nominal_expiry = before + timedelta(days=settings.agency_invite_expire_days)
    delta_seconds = abs((invitation.expires_at - nominal_expiry).total_seconds())
    assert delta_seconds <= 2


@pytest.mark.unit
def test_create_agency_invitation_rejects_duplicate_email(db, test_user):
    create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="agent@example.com",
    )
    with pytest.raises(HTTPException) as exc:
        create_agency_invitation(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            invite_email="agent@example.com",
        )
    assert exc.value.status_code == 400


@pytest.mark.unit
def test_accept_agency_invitation_creates_agent_user(db):
    invitation = create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="newagent@example.com",
    )
    user = accept_agency_invitation(
        db,
        token=invitation.token,
        full_name="New Agent",
        password="ValidPass1!",
    )
    assert user.agency_id == DEFAULT_AGENCY_ID
    assert user.role == USER_ROLE_TENANT_AGENT
    assert user.email == "newagent@example.com"

    refreshed = db.get(AgencyInvitation, invitation.id)
    assert refreshed is not None
    assert refreshed.is_used is True


@pytest.mark.unit
def test_get_valid_agency_invitation_rejects_used_token(db):
    invitation = create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="used@example.com",
    )
    invitation.is_used = True
    db.commit()
    with pytest.raises(HTTPException) as exc:
        get_valid_agency_invitation(db, invitation.token)
    assert exc.value.status_code == 400


@pytest.mark.unit
def test_update_agency_user_blocks_self_deactivation(db, test_user):
    with pytest.raises(HTTPException) as exc:
        update_agency_user(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            user_id=test_user.id,
            acting_user_id=test_user.id,
            is_active=False,
        )
    assert exc.value.status_code == 400


@pytest.mark.unit
def test_create_agency_invitation_blocked_when_subscription_locked(db, test_user):
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()

    with pytest.raises(HTTPException) as exc:
        create_agency_invitation(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            invite_email="blocked@example.com",
        )
    assert exc.value.status_code == 402


@pytest.mark.unit
def test_update_agency_user_changes_role(db, test_user):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="teamagent",
        email="teamagent@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    updated = update_agency_user(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        user_id=agent.id,
        acting_user_id=test_user.id,
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    assert updated.role == USER_ROLE_TENANT_SUPER_USER


@pytest.mark.unit
def test_cancel_agency_invitation_marks_invite_revoked(db):
    invitation = create_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="revoke-me@example.com",
    )
    cancelled = cancel_agency_invitation(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        invitation_id=invitation.id,
    )
    assert cancelled.cancelled_at is not None
    assert agency_invitation_token_status(cancelled) == "Cancelled"

    with pytest.raises(HTTPException) as exc:
        get_valid_agency_invitation(db, invitation.token)
    assert exc.value.status_code == 400
