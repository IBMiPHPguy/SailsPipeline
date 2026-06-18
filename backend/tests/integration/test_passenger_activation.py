import pytest


def _create_registry_client(client, auth_headers):
    create_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json={
            "first_name": "Pat",
            "last_name": "Inactive",
            "email": "pat@example.com",
            "phone": "5559876543",
            "cruise_lines": ["Royal Caribbean International"],
            "destination": "Caribbean",
            "destination_details": {"caribbean_regions": ["Eastern"]},
            "departure_date": "2026-07-01",
            "return_date": "2026-07-08",
            "cabin_types": ["Balcony"],
            "passengers": 1,
            "cabins_needed": 1,
        },
    )
    assert create_response.status_code == 201, create_response.text

    list_response = client.get("/api/passengers", headers=auth_headers)
    assert list_response.status_code == 200
    passenger = next(item for item in list_response.json() if item["last_name"] == "Inactive")
    return passenger["id"]


@pytest.mark.integration
def test_reactivate_client(client, auth_headers):
    passenger_id = _create_registry_client(client, auth_headers)

    deactivate_response = client.post(
        f"/api/passengers/{passenger_id}/deactivate",
        headers=auth_headers,
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    activate_response = client.post(
        f"/api/passengers/{passenger_id}/activate",
        headers=auth_headers,
    )
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True


@pytest.mark.integration
def test_reactivate_client_rejects_already_active(client, auth_headers):
    passenger_id = _create_registry_client(client, auth_headers)

    activate_response = client.post(
        f"/api/passengers/{passenger_id}/activate",
        headers=auth_headers,
    )
    assert activate_response.status_code == 400
    assert activate_response.json()["detail"] == "Client is already active."


@pytest.mark.integration
def test_reactivated_client_appears_in_search(client, auth_headers):
    passenger_id = _create_registry_client(client, auth_headers)

    client.post(f"/api/passengers/{passenger_id}/deactivate", headers=auth_headers)
    inactive_search = client.get("/api/passengers/search", params={"q": "Inactive"}, headers=auth_headers)
    assert inactive_search.status_code == 200
    assert inactive_search.json() == []

    client.post(f"/api/passengers/{passenger_id}/activate", headers=auth_headers)
    active_search = client.get("/api/passengers/search", params={"q": "Inactive"}, headers=auth_headers)
    assert active_search.status_code == 200
    assert len(active_search.json()) == 1
    assert active_search.json()[0]["id"] == passenger_id
