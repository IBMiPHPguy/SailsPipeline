import pytest
from unittest.mock import AsyncMock, patch

from app.models import Agency, User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import (
    SUBSCRIPTION_STATE_LOCKED,
    SUBSCRIPTION_STATE_PAST_DUE,
    USER_ROLE_TENANT_AGENT,
)


@pytest.mark.integration
def test_agency_team_requires_super_user(client, auth_headers, db):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="plainagent",
        email="plainagent@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(agent)
    db.commit()

    login_response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": DEFAULT_AGENCY_ORGANIZATION_HANDLE,
            "username": agent.username,
            "password": "ValidPass1!",
        },
    )
    assert login_response.status_code == 200, login_response.text
    agent_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.get("/api/agency/team", headers=agent_headers)
    assert response.status_code == 403


@pytest.mark.integration
@patch("app.routers.agency.dispatch_agency_invite_email", new_callable=AsyncMock)
def test_issue_agency_invite_and_agent_registration_flow(mock_dispatch, client, auth_headers):
    mock_dispatch.return_value = None
    invite_response = client.post(
        "/api/agency/invites",
        headers=auth_headers,
        json={"invite_email": "joiner@example.com", "role": USER_ROLE_TENANT_AGENT},
    )
    assert invite_response.status_code == 201, invite_response.text
    mock_dispatch.assert_awaited_once()
    invite_payload = invite_response.json()
    assert invite_payload["onboarding_path"].startswith("/register-agent?token=")
    token = invite_payload["onboarding_path"].split("token=", 1)[1]

    verify_response = client.get(f"/api/onboarding/agent/invites/verify?token={token}")
    assert verify_response.status_code == 200, verify_response.text
    verify_payload = verify_response.json()
    assert verify_payload["invite_email"] == "joiner@example.com"
    assert verify_payload["role"] == USER_ROLE_TENANT_AGENT

    accept_response = client.post(
        "/api/onboarding/agent/accept",
        json={
            "token": token,
            "full_name": "Joining Agent",
            "password": "ValidPass1!",
        },
    )
    assert accept_response.status_code == 200, accept_response.text
    accepted_user = accept_response.json()["user"]
    assert accepted_user["role"] == USER_ROLE_TENANT_AGENT
    assert accepted_user["email"] == "joiner@example.com"

    team_response = client.get("/api/agency/team", headers=auth_headers)
    assert team_response.status_code == 200, team_response.text
    team_payload = team_response.json()
    assert any(user["email"] == "joiner@example.com" for user in team_payload["users"])


@pytest.mark.integration
def test_patch_agency_user_updates_role(client, auth_headers, db):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="editableagent",
        email="editableagent@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    response = client.patch(
        f"/api/agency/users/{agent.id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


@pytest.mark.integration
def test_subscription_gatekeeper_blocks_dashboard_when_locked(client, auth_headers, db):
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()

    response = client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 402, response.text
    payload = response.json()
    assert payload["subscription_state"] == SUBSCRIPTION_STATE_LOCKED


@pytest.mark.integration
def test_subscription_gatekeeper_allows_auth_me_when_locked(client, auth_headers, db):
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    agency.subscription_state = SUBSCRIPTION_STATE_PAST_DUE
    db.commit()

    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200, response.text


@pytest.mark.integration
def test_subscription_gatekeeper_blocks_agency_invites_when_locked(client, auth_headers, db):
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()

    invite_response = client.post(
        "/api/agency/invites",
        headers=auth_headers,
        json={"invite_email": "shouldfail@example.com"},
    )
    assert invite_response.status_code == 402


@pytest.mark.integration
def test_revoke_agency_invitation(client, auth_headers):
    invite_response = client.post(
        "/api/agency/invites",
        headers=auth_headers,
        json={"invite_email": "revokable@example.com", "role": USER_ROLE_TENANT_AGENT},
    )
    assert invite_response.status_code == 201, invite_response.text
    invitation_id = invite_response.json()["invitation_id"]

    revoke_response = client.delete(f"/api/agency/invites/{invitation_id}", headers=auth_headers)
    assert revoke_response.status_code == 204, revoke_response.text

    team_response = client.get("/api/agency/team", headers=auth_headers)
    assert team_response.status_code == 200, team_response.text
    revoked = next(
        invite for invite in team_response.json()["invitations"] if invite["id"] == invitation_id
    )
    assert revoked["token_status"] == "Cancelled"
