import pytest
from fastapi import HTTPException

from app.models import Agency, PlatformInvitation
from app.security import hash_password
from app.services.bridge_service import (
    accept_platform_invitation,
    cancel_platform_invitation,
    create_platform_invitation,
    get_valid_platform_invitation,
    invitation_token_status,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_SUPER_USER


def test_create_platform_invitation_persists_row(db):
    invitation = create_platform_invitation(
        db,
        target_agency_name="Blue Horizon Travel",
        target_organization_handle="bluehorizon",
        invite_email="owner@bluehorizon.example",
    )
    assert invitation.id
    assert invitation.target_organization_handle == "bluehorizon"
    assert invitation.is_used is False
    assert invitation_token_status(invitation) == "Pending"


def test_accept_platform_invitation_provisions_agency_and_owner(db):
    invitation = create_platform_invitation(
        db,
        target_agency_name="Sunset Cruises",
        target_organization_handle="sunsetcruises",
        invite_email="owner@sunset.example",
    )

    owner = accept_platform_invitation(
        db,
        token=invitation.token,
        full_name="Alex Rivera",
        password="ValidPass1!",
    )

    assert owner.role == USER_ROLE_TENANT_SUPER_USER
    assert owner.agency_id != DEFAULT_AGENCY_ID

    agency = db.get(Agency, owner.agency_id)
    assert agency is not None
    assert agency.name == "Sunset Cruises"
    assert agency.organization_handle == "sunsetcruises"
    assert agency.subscription_state == SUBSCRIPTION_STATE_ACTIVE

    refreshed_invite = db.get(PlatformInvitation, invitation.id)
    assert refreshed_invite is not None
    assert refreshed_invite.is_used is True


def test_get_valid_platform_invitation_rejects_used_token(db):
    invitation = create_platform_invitation(
        db,
        target_agency_name="Used Agency",
        target_organization_handle="usedagency",
        invite_email="used@example.com",
    )
    invitation.is_used = True
    db.commit()

    with pytest.raises(HTTPException):
        get_valid_platform_invitation(db, invitation.token)


def test_create_platform_invitation_rejects_existing_agency_handle(db):
    db.add(
        Agency(
            id="00000000-0000-4000-8000-000000000099",
            name="Existing",
            slug="existing",
            organization_handle="existing",
            subscription_state=SUBSCRIPTION_STATE_ACTIVE,
            is_active=True,
        )
    )
    db.commit()

    with pytest.raises(HTTPException):
        create_platform_invitation(
            db,
            target_agency_name="Duplicate",
            target_organization_handle="existing",
            invite_email="dup@example.com",
        )


def test_cancel_platform_invitation_marks_invite_revoked(db):
    invitation = create_platform_invitation(
        db,
        target_agency_name="Cancel Me Travel",
        target_organization_handle="cancelme",
        invite_email="owner@cancelme.example",
    )
    cancelled = cancel_platform_invitation(db, invitation.id)
    assert cancelled.cancelled_at is not None
    assert invitation_token_status(cancelled) == "Cancelled"

    with pytest.raises(HTTPException):
        get_valid_platform_invitation(db, invitation.token)
