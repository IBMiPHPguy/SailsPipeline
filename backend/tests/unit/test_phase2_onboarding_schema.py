from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Agency, AgencyInvitation, PlatformInvitation, User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import (
    SUBSCRIPTION_STATE_ACTIVE,
    USER_ROLE_TENANT_AGENT,
    USER_ROLE_TENANT_SUPER_USER,
)


def test_agency_organization_handle_and_subscription_state(db):
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    assert agency is not None
    assert agency.organization_handle == DEFAULT_AGENCY_ORGANIZATION_HANDLE
    assert agency.subscription_state == SUBSCRIPTION_STATE_ACTIVE


def test_users_enforce_per_agency_email_uniqueness(db):
    db.add(
        User(
            agency_id=DEFAULT_AGENCY_ID,
            username="agent-a",
            email="shared@example.com",
            password_hash=hash_password("ValidPass1!"),
            role=USER_ROLE_TENANT_AGENT,
        )
    )
    db.commit()

    other_agency = Agency(
        id="00000000-0000-4000-8000-000000000002",
        name="Other Agency",
        slug="other",
        organization_handle="otheragency",
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    db.add(other_agency)
    db.flush()

    db.add(
        User(
            agency_id=other_agency.id,
            username="agent-b",
            email="shared@example.com",
            password_hash=hash_password("ValidPass2!"),
            role=USER_ROLE_TENANT_AGENT,
        )
    )
    db.commit()

    with pytest.raises(IntegrityError):
        db.add(
            User(
                agency_id=DEFAULT_AGENCY_ID,
                username="agent-c",
                email="shared@example.com",
                password_hash=hash_password("ValidPass3!"),
                role=USER_ROLE_TENANT_AGENT,
            )
        )
        db.commit()
    db.rollback()


def test_invitation_tables_accept_records(db):
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    platform_invite = PlatformInvitation(
        id="00000000-0000-4000-8000-000000000010",
        target_agency_name="Blue Horizon Travel",
        target_organization_handle="bluehorizon",
        invite_email="owner@bluehorizon.example",
        token="platform-token-abc",
        expires_at=expires_at,
    )
    agency_invite = AgencyInvitation(
        id="00000000-0000-4000-8000-000000000011",
        agency_id=DEFAULT_AGENCY_ID,
        invite_email="agent@example.com",
        token="agency-token-xyz",
        role=USER_ROLE_TENANT_AGENT,
        expires_at=expires_at,
    )
    db.add(platform_invite)
    db.add(agency_invite)
    db.commit()

    assert db.get(PlatformInvitation, platform_invite.id) is not None
    assert db.get(AgencyInvitation, agency_invite.id) is not None


def test_test_user_fixture_is_tenant_super_user(test_user):
    assert test_user.role == USER_ROLE_TENANT_SUPER_USER
