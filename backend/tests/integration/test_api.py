import pytest


@pytest.mark.integration
def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "cruisetravelnow-api"


@pytest.mark.integration
def test_register_and_login(client):
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "newagent",
            "email": "newagent@example.com",
            "password": "SecurePass1!",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["username"] == "newagent"

    login_response = client.post(
        "/api/auth/login",
        data={"username": "newagent", "password": "SecurePass1!"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


@pytest.mark.integration
def test_create_request_and_fetch_detail(client, auth_headers, sample_request_payload):
    create_response = client.post(
        "/api/requests",
        headers=auth_headers,
        json=sample_request_payload,
    )
    assert create_response.status_code == 201, create_response.text
    request_id = create_response.json()["id"]

    detail_response = client.get(f"/api/requests/{request_id}", headers=auth_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["first_name"] == "Jane"
    assert detail["status"] == "Open"
    assert len(detail["request_passengers"]) == 1


@pytest.mark.integration
def test_delete_draft_communication_only(client, auth_headers, sample_request_payload):
    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    request_id = create_response.json()["id"]

    draft_response = client.post(
        f"/api/requests/{request_id}/communications",
        headers=auth_headers,
        json={
            "communication_type": "research_proposal",
            "subject": "Draft proposal",
            "body": "Draft body",
            "status": "Draft",
        },
    )
    assert draft_response.status_code == 201, draft_response.text
    communication_id = draft_response.json()["id"]

    delete_response = client.delete(
        f"/api/requests/{request_id}/communications/{communication_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 204

    sent_response = client.post(
        f"/api/requests/{request_id}/communications",
        headers=auth_headers,
        json={
            "communication_type": "research_proposal",
            "subject": "Sent proposal",
            "body": "Sent body",
            "status": "Sent",
        },
    )
    sent_id = sent_response.json()["id"]

    blocked_delete = client.delete(
        f"/api/requests/{request_id}/communications/{sent_id}",
        headers=auth_headers,
    )
    assert blocked_delete.status_code == 400
    assert "draft" in blocked_delete.json()["detail"].lower()
