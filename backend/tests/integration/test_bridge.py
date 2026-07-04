import pytest

from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN, USER_ROLE_TENANT_SUPER_USER


BRIDGE_ADMIN_PASSWORD = "BridgePass1!"


@pytest.fixture
def bridge_admin_user(db) -> "User":
    from app.models import User
    from app.security import hash_password

    user = User(
        agency_id=None,
        username="bridgeadmin",
        email="bridgeadmin@example.com",
        password_hash=hash_password(BRIDGE_ADMIN_PASSWORD),
        role=USER_ROLE_PLATFORM_SUPER_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def bridge_admin_headers(client, bridge_admin_user):
    response = client.post(
        "/api/auth/bridge/login",
        json={
            "username": bridge_admin_user.username,
            "password": BRIDGE_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
def test_bridge_login_rejects_tenant_user(client, test_user):
    response = client.post(
        "/api/auth/bridge/login",
        json={"username": test_user.username, "password": "TestPassword1!"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_bridge_summary_forbidden_for_tenant_super_user(client, auth_headers):
    response = client.get("/api/bridge/summary", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.integration
def test_bridge_summary_lists_agencies_and_invitations(client, bridge_admin_headers, bridge_admin_user):
    response = client.get("/api/bridge/summary", headers=bridge_admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert any(agency["id"] == DEFAULT_AGENCY_ID for agency in payload["agencies"])
    assert isinstance(payload["invitations"], list)


@pytest.mark.integration
def test_issue_platform_invitation_and_onboarding_flow(client, bridge_admin_headers):
    invite_response = client.post(
        "/api/bridge/invites",
        headers=bridge_admin_headers,
        json={
            "target_agency_name": "Harbor Lights Travel",
            "target_organization_handle": "harborlights",
            "invite_email": "owner@harborlights.example",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invite_payload = invite_response.json()
    assert invite_payload["onboarding_path"].startswith("/onboarding?token=")
    token = invite_payload["onboarding_path"].split("token=", 1)[1]

    verify_response = client.get(f"/api/onboarding/invites/verify?token={token}")
    assert verify_response.status_code == 200
    verify_payload = verify_response.json()
    assert verify_payload["organization_handle"] == "harborlights"
    assert verify_payload["invite_email"] == "owner@harborlights.example"

    accept_response = client.post(
        "/api/onboarding/accept",
        json={
            "token": token,
            "full_name": "Jordan Lee",
            "password": "ValidPass1!",
        },
    )
    assert accept_response.status_code == 200, accept_response.text
    auth_payload = accept_response.json()
    assert auth_payload["user"]["role"] == USER_ROLE_TENANT_SUPER_USER
    assert auth_payload["user"]["email"] == "owner@harborlights.example"
    assert auth_payload["user"]["agency_id"] != DEFAULT_AGENCY_ID

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {auth_payload['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["role"] == USER_ROLE_TENANT_SUPER_USER

    reused_verify = client.get(f"/api/onboarding/invites/verify?token={token}")
    assert reused_verify.status_code == 400


@pytest.mark.integration
def test_bridge_tenant_detail_and_update(client, bridge_admin_headers, db):
    from app.models import Agency, User
    from app.security import hash_password

    detail_response = client.get(
        f"/api/bridge/tenants/{DEFAULT_AGENCY_ID}",
        headers=bridge_admin_headers,
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["agency"]["organization_handle"] == "default"
    assert isinstance(detail["users"], list)

    update_response = client.patch(
        f"/api/bridge/tenants/{DEFAULT_AGENCY_ID}",
        headers=bridge_admin_headers,
        json={
            "name": "Default Agency Updated",
            "organization_handle": "default",
            "subscription_state": "Trialing",
        },
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["name"] == "Default Agency Updated"
    assert update_response.json()["subscription_state"] == "Trialing"

    other_agency = Agency(
        id="00000000-0000-4000-8000-000000000088",
        name="Harbor Lights Travel",
        slug="harborlights",
        organization_handle="harborlights",
        subscription_state="Active",
        is_active=True,
    )
    db.add(other_agency)
    db.add(
        User(
            agency_id=other_agency.id,
            username="harbor-owner",
            email="owner@harborlights.example",
            password_hash=hash_password("ValidPass1!"),
            role=USER_ROLE_TENANT_SUPER_USER,
        )
    )
    db.commit()

    tenant_response = client.get(
        f"/api/bridge/tenants/{other_agency.id}",
        headers=bridge_admin_headers,
    )
    assert tenant_response.status_code == 200
    assert len(tenant_response.json()["users"]) == 1


@pytest.mark.integration
def test_bridge_tenant_update_rejects_duplicate_handle(client, bridge_admin_headers, db):
    from app.models import Agency

    db.add(
        Agency(
            id="00000000-0000-4000-8000-000000000087",
            name="Other Agency",
            slug="otheragency",
            organization_handle="otheragency",
            subscription_state="Active",
            is_active=True,
        )
    )
    db.commit()

    response = client.patch(
        f"/api/bridge/tenants/{DEFAULT_AGENCY_ID}",
        headers=bridge_admin_headers,
        json={
            "name": "Default Agency",
            "organization_handle": "otheragency",
            "subscription_state": "Active",
        },
    )
    assert response.status_code == 400


@pytest.mark.integration
def test_revoke_platform_invitation(client, bridge_admin_headers):
    invite_response = client.post(
        "/api/bridge/invites",
        headers=bridge_admin_headers,
        json={
            "target_agency_name": "Revoked Travel",
            "target_organization_handle": "revokedtravel",
            "invite_email": "owner@revokedtravel.example",
        },
    )
    assert invite_response.status_code == 201, invite_response.text
    invitation_id = invite_response.json()["invitation_id"]

    revoke_response = client.delete(
        f"/api/bridge/invites/{invitation_id}",
        headers=bridge_admin_headers,
    )
    assert revoke_response.status_code == 204, revoke_response.text

    summary_response = client.get("/api/bridge/summary", headers=bridge_admin_headers)
    assert summary_response.status_code == 200, summary_response.text
    revoked = next(
        invite for invite in summary_response.json()["invitations"] if invite["id"] == invitation_id
    )
    assert revoked["token_status"] == "Cancelled"
