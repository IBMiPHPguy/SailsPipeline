from datetime import date

import pytest

from app.models import User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_ORGANIZATION_HANDLE
from app.tenant_roles import USER_ROLE_TENANT_AGENT


def _group_payload(**overrides):
    payload = {
        "group_name": "Alaska Alumni 2028",
        "cruise_line": "Holland America Line",
        "ship_name": "Nieuw Amsterdam",
        "sailing_date": "2028-06-01",
        "disembarkation_date": "2028-06-08",
        "group_id_code": "ALASKA-2028",
        "group_amenities": "Welcome reception",
        "tc_ratio": "1:16",
        "inventory_items": [
            {
                "cabin_category": "VN",
                "cabin_type": "Ocean View",
                "cabin_description": "Partial view",
                "price_per_cabin": 1499,
                "cabins_allocated": 8,
                "cabins_reserved": 0,
            }
        ],
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def agent_headers(client, db):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="groupagent",
        email="groupagent@example.com",
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
def test_list_agency_groups_requires_super_user(client, agent_headers):
    response = client.get("/api/agency-groups", headers=agent_headers)
    assert response.status_code == 403


@pytest.mark.integration
def test_agency_group_crud_flow(client, auth_headers):
    create_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    group_id = created["id"]
    assert created["group_name"] == "Alaska Alumni 2028"
    assert created["summary"]["total_cabins_allocated"] == 8
    assert len(created["inventory_items"]) == 1

    list_response = client.get("/api/agency-groups?is_active=true", headers=auth_headers)
    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()
    assert listed["total"] >= 1
    assert any(item["id"] == group_id for item in listed["items"])

    patch_response = client.patch(
        f"/api/agency-groups/{group_id}",
        headers=auth_headers,
        json={"group_name": "Alaska Alumni Block 2028"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["group_name"] == "Alaska Alumni Block 2028"

    inventory_id = created["inventory_items"][0]["id"]
    inventory_response = client.patch(
        f"/api/agency-groups/inventory/{inventory_id}",
        headers=auth_headers,
        json={"cabins_allocated": 10, "price_per_cabin": 1599},
    )
    assert inventory_response.status_code == 200, inventory_response.text
    updated_inventory = inventory_response.json()["inventory_items"][0]
    assert updated_inventory["cabins_allocated"] == 10
    assert updated_inventory["cabins_remaining"] == 10

    add_inventory_response = client.post(
        f"/api/agency-groups/{group_id}/inventory",
        headers=auth_headers,
        json={
            "cabin_category": "SA",
            "cabin_type": "Suite",
            "price_per_cabin": 3999,
            "cabins_allocated": 2,
            "cabins_reserved": 0,
        },
    )
    assert add_inventory_response.status_code == 201, add_inventory_response.text
    assert len(add_inventory_response.json()["inventory_items"]) == 2

    archive_response = client.post(f"/api/agency-groups/{group_id}/archive", headers=auth_headers)
    assert archive_response.status_code == 200, archive_response.text
    assert archive_response.json()["is_active"] is False

    archived_list_response = client.get("/api/agency-groups?is_active=false", headers=auth_headers)
    assert archived_list_response.status_code == 200, archived_list_response.text
    archived_listed = archived_list_response.json()
    assert any(item["id"] == group_id for item in archived_listed["items"])

    delete_inventory_response = client.delete(
        f"/api/agency-groups/inventory/{inventory_id}",
        headers=auth_headers,
    )
    assert delete_inventory_response.status_code == 200, delete_inventory_response.text
    assert len(delete_inventory_response.json()["inventory_items"]) == 1


@pytest.mark.integration
def test_agent_can_read_group_detail(client, auth_headers, agent_headers):
    create_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(group_name="Agent Readable Group"),
    )
    assert create_response.status_code == 201, create_response.text
    group_id = create_response.json()["id"]

    detail_response = client.get(f"/api/agency-groups/{group_id}", headers=agent_headers)
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["group_name"] == "Agent Readable Group"

    patch_response = client.patch(
        f"/api/agency-groups/{group_id}",
        headers=agent_headers,
        json={"group_name": "Blocked"},
    )
    assert patch_response.status_code == 403


@pytest.mark.integration
def test_cannot_delete_inventory_with_reserved_cabins(client, auth_headers):
    create_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_response.status_code == 201, create_response.text
    inventory_id = create_response.json()["inventory_items"][0]["id"]

    reserve_response = client.patch(
        f"/api/agency-groups/inventory/{inventory_id}",
        headers=auth_headers,
        json={"cabins_reserved": 2},
    )
    assert reserve_response.status_code == 200, reserve_response.text

    delete_response = client.delete(
        f"/api/agency-groups/inventory/{inventory_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 400, delete_response.text
    assert "reserved" in delete_response.json()["detail"].lower()


@pytest.mark.integration
def test_create_group_rejects_invalid_dates(client, auth_headers):
    response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(
            sailing_date=date(2028, 6, 8).isoformat(),
            disembarkation_date=date(2028, 6, 1).isoformat(),
        ),
    )
    assert response.status_code == 400, response.text


@pytest.mark.integration
def test_list_agency_groups_search_and_pagination(client, auth_headers):
    for index in range(8):
        response = client.post(
            "/api/agency-groups",
            headers=auth_headers,
            json=_group_payload(
                group_name=f"Search Block {index}",
                ship_name=f"Search Ship {index}",
                group_id_code=f"SEARCH-{index}",
            ),
        )
        assert response.status_code == 201, response.text

    page_one = client.get("/api/agency-groups?is_active=true&page=1&page_size=7", headers=auth_headers)
    assert page_one.status_code == 200, page_one.text
    page_one_payload = page_one.json()
    assert len(page_one_payload["items"]) == 7
    assert page_one_payload["page_size"] == 7
    assert page_one_payload["total"] >= 8
    assert page_one_payload["total_pages"] >= 2

    page_two = client.get("/api/agency-groups?is_active=true&page=2&page_size=7", headers=auth_headers)
    assert page_two.status_code == 200, page_two.text
    assert len(page_two.json()["items"]) >= 1

    search_response = client.get(
        "/api/agency-groups?is_active=true&q=Holland%20Search%20Ship%203",
        headers=auth_headers,
    )
    assert search_response.status_code == 200, search_response.text
    search_payload = search_response.json()
    assert search_payload["total"] == 1
    assert search_payload["items"][0]["ship_name"] == "Search Ship 3"
