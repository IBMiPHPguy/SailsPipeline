from datetime import timedelta

import pytest

from app.models import Agency, User
from app.security import create_access_token, hash_password
from app.services.subscription_service import utc_now
from app.tenant_roles import SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_TRIALING, USER_ROLE_TENANT_SUPER_USER

LOGIN_PASSWORD = "AgencyPass1!"


@pytest.fixture
def locked_trial_agency(db):
    agency = Agency(
        id="locked-trial-agency-01",
        name="Locked Demo Travel",
        slug="locked-demo",
        organization_handle="locked-demo",
        subscription_state=SUBSCRIPTION_STATE_LOCKED,
        trial_ends_at=utc_now() - timedelta(days=1),
        is_active=True,
    )
    user = User(
        agency_id=agency.id,
        username="locked.owner",
        email="owner@lockeddemo.example",
        password_hash=hash_password(LOGIN_PASSWORD),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(agency)
    db.add(user)
    db.commit()
    db.refresh(user)
    return agency, user


@pytest.mark.integration
def test_openapi_docs_available_without_auth(client):
    docs_response = client.get("/docs")
    assert docs_response.status_code == 200, docs_response.text
    assert "swagger-ui" in docs_response.text.lower()

    schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200, schema_response.text
    payload = schema_response.json()
    assert payload["info"]["title"] == "SailsPipeline API"
    assert "/api/health" in payload["paths"]


@pytest.mark.integration
def test_openapi_docs_ignore_locked_tenant_bearer_token(client, locked_trial_agency):
    _, user = locked_trial_agency
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    headers = {"Authorization": f"Bearer {token}"}

    docs_response = client.get("/docs", headers=headers)
    assert docs_response.status_code == 200, docs_response.text

    schema_response = client.get("/openapi.json", headers=headers)
    assert schema_response.status_code == 200, schema_response.text
    assert schema_response.json()["paths"]

    assets_response = client.get("/static/swaggerui/swagger-ui-bundle.js", headers=headers)
    assert assets_response.status_code == 200, assets_response.text


@pytest.mark.integration
def test_locked_tenant_token_still_blocked_on_crm_api(client, locked_trial_agency):
    _, user = locked_trial_agency
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )

    response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 402, response.text
