import pytest

from app.models import Agency, AgencySettings, User
from app.services.public_registration_service import PUBLIC_REGISTRATION_SUCCESS_MESSAGE
from app.tenant_roles import SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_TRIALING, USER_ROLE_TENANT_SUPER_USER


REGISTER_PASSWORD = "AgencyPass1!"


@pytest.mark.integration
def test_public_register_provisions_tenant_workspace(client, db):
    response = client.post(
        "/api/public/register",
        json={
            "agency_name": "Sunset Voyages",
            "admin_name": "Jordan Lee",
            "admin_email": "jordan@sunsetvoyages.example",
            "password": REGISTER_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["access_token"]
    assert payload["user"]["role"] == USER_ROLE_TENANT_SUPER_USER
    assert payload["user"]["email"] == "jordan@sunsetvoyages.example"

    agency = db.get(Agency, payload["user"]["agency_id"])
    assert agency is not None
    assert agency.name == "Sunset Voyages"
    assert agency.organization_handle == "sunset-voyages"
    assert agency.subscription_state == SUBSCRIPTION_STATE_TRIALING
    assert agency.trial_ends_at is not None

    settings = db.get(AgencySettings, agency.id)
    assert settings is not None
    assert settings.agency_name == "Sunset Voyages"
    assert settings.primary_color == "#0d5c75"
    assert settings.secondary_color == "#17a2b8"
    assert (settings.custom_master_tc or "").strip()


@pytest.mark.integration
def test_public_register_suppresses_duplicate_email_enumeration(client, db):
    first = client.post(
        "/api/public/register",
        json={
            "agency_name": "First Agency",
            "admin_name": "Alex Morgan",
            "admin_email": "duplicate@example.com",
            "password": REGISTER_PASSWORD,
        },
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/public/register",
        json={
            "agency_name": "Second Agency",
            "admin_name": "Alex Morgan",
            "admin_email": "duplicate@example.com",
            "password": REGISTER_PASSWORD,
        },
    )
    assert second.status_code == 200, second.text
    payload = second.json()
    assert payload["message"] == PUBLIC_REGISTRATION_SUCCESS_MESSAGE
    assert "already exists" not in payload["message"].lower()
    assert "access_token" not in payload


@pytest.mark.integration
def test_public_register_token_allows_dashboard_access(client):
    response = client.post(
        "/api/public/register",
        json={
            "agency_name": "Harbor Peak Travel",
            "admin_name": "Sam Rivera",
            "admin_email": "sam@harborpeak.example",
            "password": REGISTER_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200, me_response.text

    dashboard_response = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dashboard_response.status_code == 200, dashboard_response.text
