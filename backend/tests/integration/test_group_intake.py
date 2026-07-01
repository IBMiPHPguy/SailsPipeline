import pytest

from app.models import User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import USER_ROLE_TENANT_AGENT

from tests.integration.test_agency_groups_api import _group_payload


@pytest.fixture
def agent_headers(client, db):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="groupintakeagent",
        email="groupintakeagent@example.com",
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


def _group_block_request_payload(group_id: str, inventory_id: str, **overrides):
    payload = {
        "first_name": "Group",
        "last_name": "Guest",
        "email": "groupguest@example.com",
        "phone": "555-010-2000",
        "cruise_lines": ["Holland America Line"],
        "excluded_cruise_lines": [],
        "destination": "Caribbean",
        "destination_details": {"caribbean_regions": ["Eastern"]},
        "departure_date": "2028-06-01",
        "return_date": "2028-06-08",
        "cabin_types": ["Ocean View"],
        "passengers": 2,
        "cabins_needed": 2,
        "ship_name": "Nieuw Amsterdam",
        "group_id": group_id,
        "group_bookings": [
            {
                "group_inventory_id": inventory_id,
                "cabins_requested": 2,
            }
        ],
    }
    payload.update(overrides)
    return payload


@pytest.mark.integration
def test_active_group_picker_available_to_agents(client, auth_headers, agent_headers):
    create_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    group_id = create_response.json()["id"]

    picker_response = client.get("/api/agency-groups/active-picker?q=Alaska", headers=agent_headers)
    assert picker_response.status_code == 200, picker_response.text
    items = picker_response.json()
    assert any(item["id"] == group_id for item in items)


@pytest.mark.integration
def test_group_inventory_options_for_selected_group(client, auth_headers, agent_headers):
    create_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    group_id = created["id"]
    inventory_id = created["inventory_items"][0]["id"]

    options_response = client.get(
        f"/api/agency-groups/{group_id}/inventory-options",
        headers=agent_headers,
    )
    assert options_response.status_code == 200, options_response.text
    options = options_response.json()
    assert len(options) == 1
    assert options[0]["id"] == inventory_id
    assert options[0]["is_selectable"] is True
    assert "Partial view" in options[0]["label"]


@pytest.mark.integration
def test_create_request_with_group_bookings(client, auth_headers):
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

    detail_response = client.get(f"/api/requests/{request_id}", headers=auth_headers)
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["group_id"] == created_group["id"]
    assert detail["group_inventory_id"] == inventory_id
    assert detail["group_summary"]["group_name"] == "Alaska Alumni 2028"
    assert len(detail["group_bookings"]) == 1
    assert detail["group_bookings"][0]["cabins_requested"] == 2
    assert detail["cabins_needed"] == 2
    assert len(detail["proposed_cruises"]) == 1
    proposed = detail["proposed_cruises"][0]
    assert proposed["ship"] == "Nieuw Amsterdam"
    assert proposed["cruise_line"] == "Holland America Line"
    assert proposed["departure_date"] == "2028-06-01"
    assert proposed["number_of_nights"] == 7
    assert len(proposed["cabin_rooms"]) == 2
    assert proposed["cabin_rooms"][0]["room_category"] == "Partial view (VN)"
    assert float(proposed["cabin_rooms"][0]["deposit_amount"]) == 250.0
    assert float(proposed["deposit_amount"]) == 500.0
    assert float(proposed["cost"]) == 2998.0


@pytest.mark.integration
def test_create_request_rejects_mismatched_group_inventory(client, auth_headers):
    first_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(group_name="Group A"),
    )
    second_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(group_name="Group B", group_id_code="GROUP-B"),
    )
    assert first_group_response.status_code == 201
    assert second_group_response.status_code == 201

    wrong_inventory_id = second_group_response.json()["inventory_items"][0]["id"]
    create_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json=_group_block_request_payload(first_group_response.json()["id"], wrong_inventory_id),
    )
    assert create_request_response.status_code == 400
    assert "does not belong" in create_request_response.json()["detail"]


@pytest.mark.integration
def test_create_request_rejects_group_field_mismatch(client, auth_headers):
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
        json=_group_block_request_payload(
            created_group["id"],
            inventory_id,
            departure_date="2028-06-02",
        ),
    )
    assert create_request_response.status_code == 400
    assert "Departure date must match" in create_request_response.json()["detail"]
