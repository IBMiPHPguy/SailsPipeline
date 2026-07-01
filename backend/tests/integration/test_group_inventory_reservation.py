import pytest

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED
from tests.integration.test_agency_groups_api import _group_payload
from tests.integration.test_group_intake import _group_block_request_payload


@pytest.mark.integration
def test_purchased_close_reserves_group_inventory(client, auth_headers):
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

    close_response = client.patch(
        f"/api/requests/{request_id}",
        headers=auth_headers,
        json={
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": PRIMARY_CLOSE_REASON,
        },
    )
    assert close_response.status_code == 200, close_response.text

    group_response = client.get(f"/api/agency-groups/{created_group['id']}", headers=auth_headers)
    assert group_response.status_code == 200, group_response.text
    inventory = group_response.json()["inventory_items"][0]
    assert inventory["cabins_reserved"] == 2
    assert inventory["cabins_remaining"] == 6

    detail_response = client.get(f"/api/requests/{request_id}", headers=auth_headers)
    assert detail_response.status_code == 200, detail_response.text
    assert detail_response.json()["group_inventory_reservation_applied"] is True


@pytest.mark.integration
def test_purchased_close_rejects_when_inventory_insufficient(client, auth_headers):
    create_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(
            inventory_items=[
                {
                    "cabin_category": "VN",
                    "cabin_type": "Ocean View",
                    "cabin_description": "Partial view",
                    "price_per_cabin": 1499,
                    "deposit_per_cabin": 250,
                    "cabins_allocated": 3,
                    "cabins_reserved": 0,
                }
            ]
        ),
    )
    assert create_group_response.status_code == 201, create_group_response.text
    created_group = create_group_response.json()
    inventory_id = created_group["inventory_items"][0]["id"]

    first_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json=_group_block_request_payload(created_group["id"], inventory_id, cabins_needed=2),
    )
    assert first_request_response.status_code == 201, first_request_response.text
    first_request_id = first_request_response.json()["id"]

    second_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json=_group_block_request_payload(
            created_group["id"],
            inventory_id,
            email="secondguest@example.com",
            cabins_needed=2,
        ),
    )
    assert second_request_response.status_code == 201, second_request_response.text
    second_request_id = second_request_response.json()["id"]

    first_close_response = client.patch(
        f"/api/requests/{first_request_id}",
        headers=auth_headers,
        json={
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": PRIMARY_CLOSE_REASON,
        },
    )
    assert first_close_response.status_code == 200, first_close_response.text

    blocked_close_response = client.patch(
        f"/api/requests/{second_request_id}",
        headers=auth_headers,
        json={
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": PRIMARY_CLOSE_REASON,
        },
    )
    assert blocked_close_response.status_code == 400, blocked_close_response.text
    assert "Only 1 cabins remain" in blocked_close_response.text

    still_open_response = client.get(f"/api/requests/{second_request_id}", headers=auth_headers)
    assert still_open_response.status_code == 200, still_open_response.text
    assert still_open_response.json()["status"] == "Open"


@pytest.mark.integration
def test_non_group_purchased_close_does_not_touch_inventory(client, auth_headers):
    create_group_response = client.post(
        "/api/agency-groups",
        headers=auth_headers,
        json=_group_payload(),
    )
    assert create_group_response.status_code == 201, create_group_response.text
    created_group = create_group_response.json()
    inventory_id = created_group["inventory_items"][0]["id"]
    initial_reserved = created_group["inventory_items"][0]["cabins_reserved"]

    create_request_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json={
            "first_name": "Standard",
            "last_name": "Guest",
            "email": "standardguest@example.com",
            "phone": "555-010-3000",
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

    group_response = client.get(f"/api/agency-groups/{created_group['id']}", headers=auth_headers)
    assert group_response.status_code == 200, group_response.text
    inventory = next(item for item in group_response.json()["inventory_items"] if item["id"] == inventory_id)
    assert inventory["cabins_reserved"] == initial_reserved
