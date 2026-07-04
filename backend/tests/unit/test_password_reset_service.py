from app.models import Agency, User
from app.security import hash_password
from app.services.password_reset_service import find_active_tenant_user_for_password_reset
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_AGENT


def test_password_reset_lookup_scopes_by_organization_handle(db):
    shared_email = "shared@example.com"
    db.add(
        User(
            agency_id=DEFAULT_AGENCY_ID,
            username="agent-a",
            email=shared_email,
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

    other_user = User(
        agency_id=other_agency.id,
        username="agent-b",
        email=shared_email,
        password_hash=hash_password("ValidPass2!"),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(other_user)
    db.commit()

    default_match = find_active_tenant_user_for_password_reset(
        db,
        organization_handle=DEFAULT_AGENCY_ORGANIZATION_HANDLE,
        email=shared_email,
    )
    other_match = find_active_tenant_user_for_password_reset(
        db,
        organization_handle="otheragency",
        email=shared_email,
    )
    missing_match = find_active_tenant_user_for_password_reset(
        db,
        organization_handle="unknown-agency",
        email=shared_email,
    )

    assert default_match is not None
    assert default_match.username == "agent-a"
    assert other_match is not None
    assert other_match.username == "agent-b"
    assert missing_match is None
