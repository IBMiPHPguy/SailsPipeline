import pytest

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED
from app.models import User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import USER_ROLE_TENANT_AGENT
from tests.integration.test_agency_groups_api import _group_payload
from tests.integration.test_group_intake import _group_block_request_payload


@pytest.fixture
def agent_headers(client, db):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="groupmetricsagent",
        email="groupmetricsagent@example.com",
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
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


@pytest.mark.integration
def test_group_metrics_endpoint_returns_operational_totals(client, auth_headers, agent_headers):
    create_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_group_response.status_code == 201, create_group_response.text
    created_group = create_group_response.json()
    inventory_id = created_group["inventory_items"][0]["id"]

    create_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json=_group_block_request_payload(created_group["id"], inventory_id),
    )
    assert create_request_response.status_code == 201, create_request_response.text
    request_id = create_request_response.json()["id"]

    metrics_before = client.get(
        f"/api/agency-groups/{created_group['id']}/metrics",
        headers=agent_headers,
    )
    assert metrics_before.status_code == 200, metrics_before.text
    before = metrics_before.json()
    assert before["linked_request_count"] == 1
    assert before["totals"]["cabins_reserved"] == 0
    assert before["totals"]["max_gross_yield"] == 11992.0
    assert before["tour_conductor"]["berths_per_credit"] == 16
    assert before["inventory_rows"][0]["liquidation_tone"] == "healthy"

    close_response = client.patch(
        f"/api/requests/{request_id}",
        headers=auth_headers,
        json={
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": PRIMARY_CLOSE_REASON,
        },
    )
    assert close_response.status_code == 200, close_response.text

    metrics_after = client.get(
        f"/api/agency-groups/{created_group['id']}/metrics",
        headers=agent_headers,
    )
    assert metrics_after.status_code == 200, metrics_after.text
    after = metrics_after.json()
    assert after["totals"]["cabins_reserved"] == 2
    assert after["totals"]["accrued_gross_yield"] == 2998.0
    assert after["totals"]["remaining_gross_yield"] == 8994.0
    assert after["inventory_rows"][0]["liquidation_percent"] == 25.0
    assert after["tour_conductor"]["total_berths_reserved"] == 4
    assert after["tour_conductor"]["berths_until_next_tc"] == 12
    assert "12 more berths" in after["tour_conductor"]["message"]


@pytest.mark.integration
def test_unlinked_request_close_does_not_change_group_metrics(client, auth_headers):
    create_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_group_response.status_code == 201, create_group_response.text
    group_id = create_group_response.json()["id"]

    create_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json={
            "first_name": "Standard",
            "last_name": "Guest",
            "email": "metrics-guest@example.com",
            "phone": "555-010-4000",
            "cruise_lines": ["Holland America Line"],
            "excluded_cruise_lines": [],
            "destination": "Caribbean",
            "destination_details": {"caribbean_regions": ["Eastern"]},
            "departure_date": "2028-06-01",
            "return_date": "2028-06-08",
            "cabin_types": ["Ocean View"],
            "passengers": 2,
            "cabins_needed": 1,
            "ship_name": "Nieuw Amsterdam",
        },
    )
    assert create_request_response.status_code == 201, create_request_response.text
    request_id = create_request_response.json()["id"]

    close_response = client.patch(
        f"/api/requests/{request_id}",
        headers=auth_headers,
        json={
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": PRIMARY_CLOSE_REASON,
        },
    )
    assert close_response.status_code == 200, close_response.text

    metrics_response = client.get(f"/api/agency-groups/{group_id}/metrics", headers=auth_headers)
    assert metrics_response.status_code == 200, metrics_response.text
    metrics = metrics_response.json()
    assert metrics["linked_request_count"] == 0
    assert metrics["totals"]["cabins_reserved"] == 0
