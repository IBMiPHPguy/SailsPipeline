"""Cross-tenant isolation: another agency's IDs must return 404, not leak data."""

import pytest

from app.models import Agency, Passenger, User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_AGENT

OTHER_AGENCY_ID = "00000000-0000-4000-8000-000000000002"
OTHER_AGENCY_PASSWORD = "OtherPass1!"


@pytest.fixture
def other_agency_user(db) -> User:
    db.add(
        Agency(
            id=OTHER_AGENCY_ID,
            name="Other Test Agency",
            slug="other-test",
            organization_handle="other-test",
            subscription_state=SUBSCRIPTION_STATE_ACTIVE,
            is_active=True,
        )
    )
    user = User(
        agency_id=OTHER_AGENCY_ID,
        username="otheragencyagent",
        email="otheragency@example.com",
        password_hash=hash_password(OTHER_AGENCY_PASSWORD),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_agency_auth_headers(client, other_agency_user):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "other-test",
            "username": other_agency_user.username,
            "password": OTHER_AGENCY_PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def default_agency_passenger(db, test_user) -> Passenger:
    passenger = Passenger(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Default",
        last_name="TenantClient",
        email="default-tenant@example.com",
        phone="555-0001",
        qualifiers=[],
        created_by_id=test_user.id,
    )
    db.add(passenger)
    db.commit()
    db.refresh(passenger)
    return passenger


@pytest.mark.integration
def test_cross_tenant_request_detail_returns_404(
    client,
    auth_headers,
    other_agency_auth_headers,
    sample_request_payload,
):
    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    assert create_response.status_code == 201, create_response.text
    request_id = create_response.json()["id"]

    own_response = client.get(f"/api/requests/{request_id}", headers=auth_headers)
    assert own_response.status_code == 200

    cross_response = client.get(f"/api/requests/{request_id}", headers=other_agency_auth_headers)
    assert cross_response.status_code == 404
    assert cross_response.json()["detail"] == "Not found."


@pytest.mark.integration
def test_cross_tenant_request_notes_returns_404(
    client,
    auth_headers,
    other_agency_auth_headers,
    sample_request_payload,
):
    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    request_id = create_response.json()["id"]

    cross_response = client.get(f"/api/requests/{request_id}/notes", headers=other_agency_auth_headers)
    assert cross_response.status_code == 404
    assert cross_response.json()["detail"] == "Not found."


@pytest.mark.integration
def test_cross_tenant_passenger_registry_returns_404(
    client,
    auth_headers,
    other_agency_auth_headers,
    default_agency_passenger,
):
    own_response = client.get(
        f"/api/passengers/{default_agency_passenger.id}",
        headers=auth_headers,
    )
    assert own_response.status_code == 200

    cross_response = client.get(
        f"/api/passengers/{default_agency_passenger.id}",
        headers=other_agency_auth_headers,
    )
    assert cross_response.status_code == 404
    assert cross_response.json()["detail"] == "Not found."


@pytest.mark.integration
def test_cross_tenant_open_requests_list_excludes_other_agency_data(
    client,
    auth_headers,
    other_agency_auth_headers,
    sample_request_payload,
):
    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    assert create_response.status_code == 201
    request_id = create_response.json()["id"]

    other_list = client.get("/api/requests/open", headers=other_agency_auth_headers)
    assert other_list.status_code == 200
    other_ids = {item["id"] for item in other_list.json()["items"]}
    assert request_id not in other_ids

    own_list = client.get("/api/requests/open", headers=auth_headers)
    assert own_list.status_code == 200
    own_ids = {item["id"] for item in own_list.json()["items"]}
    assert request_id in own_ids
