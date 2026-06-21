import pytest

from app.models import Agency, User
from app.security import hash_password
from app.services.auth_service import authenticate_agency_user, resolve_agency_by_organization_handle
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_AGENT


def test_resolve_agency_by_organization_handle_is_case_insensitive(db):
    agency = resolve_agency_by_organization_handle(db, "DEFAULT")
    assert agency is not None
    assert agency.id == DEFAULT_AGENCY_ID
    assert agency.organization_handle == DEFAULT_AGENCY_ORGANIZATION_HANDLE


def test_resolve_agency_by_organization_handle_returns_none_for_unknown(db):
    assert resolve_agency_by_organization_handle(db, "no-such-tenant") is None


def test_authenticate_agency_user_scopes_to_organization(db, test_user):
    user = authenticate_agency_user(
        db,
        organization_handle=DEFAULT_AGENCY_ORGANIZATION_HANDLE,
        username=test_user.username,
        password="TestPassword1!",
    )
    assert user is not None
    assert user.id == test_user.id
    assert user.agency_id == DEFAULT_AGENCY_ID


def test_authenticate_agency_user_rejects_wrong_organization(db, test_user):
    other_agency = Agency(
        id="00000000-0000-4000-8000-000000000099",
        name="Ghost Agency",
        slug="ghost",
        organization_handle="ghost",
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    db.add(other_agency)
    db.commit()

    assert (
        authenticate_agency_user(
            db,
            organization_handle="ghost",
            username=test_user.username,
            password="TestPassword1!",
        )
        is None
    )


def test_authenticate_agency_user_rejects_invalid_password(db, test_user):
    assert (
        authenticate_agency_user(
            db,
            organization_handle=DEFAULT_AGENCY_ORGANIZATION_HANDLE,
            username=test_user.username,
            password="WrongPass1!",
        )
        is None
    )


def test_authenticate_agency_user_rejects_inactive_user(db):
    inactive_user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="inactive-agent",
        email="inactive@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
        is_active=False,
    )
    db.add(inactive_user)
    db.commit()

    assert (
        authenticate_agency_user(
            db,
            organization_handle=DEFAULT_AGENCY_ORGANIZATION_HANDLE,
            username="inactive-agent",
            password="ValidPass1!",
        )
        is None
    )
