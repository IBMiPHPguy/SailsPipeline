import pytest


@pytest.mark.integration
def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "sailspipeline-api"


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
        json={
            "organization_handle": "default",
            "username": "newagent",
            "password": "SecurePass1!",
        },
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


@pytest.mark.integration
def test_login_requires_valid_organization_handle(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "unknown-tenant",
            "username": test_user.username,
            "password": "TestPassword1!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect organization handle, username, or password."


@pytest.mark.integration
def test_login_token_includes_tenant_claims(client, test_user):
    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "default",
            "username": test_user.username,
            "password": "TestPassword1!",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    from app.security import decode_access_token

    claims = decode_access_token(token)
    assert claims.user_id == test_user.id
    assert claims.agency_id == test_user.agency_id
    assert claims.role == test_user.role
    assert claims.username == test_user.username


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


@pytest.mark.integration
def test_closed_requests_search_and_pagination(client, auth_headers, sample_request_payload, db, test_user):
    from app.constants import REQUEST_STATUS_CLOSED
    from app.models import TravelRequest

    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    request_id = create_response.json()["id"]
    request = db.get(TravelRequest, request_id)
    request.status = REQUEST_STATUS_CLOSED
    request.close_reason = "Client declined"
    db.commit()

    list_response = client.get("/api/requests/closed", headers=auth_headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 25
    assert payload["total_pages"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["first_name"] == "Jane"

    search_response = client.get("/api/requests/closed?q=declined", headers=auth_headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1

    miss_response = client.get("/api/requests/closed?q=Alaska", headers=auth_headers)
    assert miss_response.status_code == 200
    assert miss_response.json()["total"] == 0


@pytest.mark.integration
def test_open_requests_search_and_pagination(client, auth_headers, sample_request_payload):
    create_response = client.post("/api/requests", headers=auth_headers, json=sample_request_payload)
    assert create_response.status_code == 201, create_response.text

    list_response = client.get("/api/requests/open", headers=auth_headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 25
    assert payload["total_pages"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["first_name"] == "Jane"
    assert "is_stale" in payload["items"][0]

    dashboard_response = client.get("/api/dashboard", headers=auth_headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["open_count"] == 1
    assert dashboard["total_pipeline_value"] == 0.0
    assert "open_requests" not in dashboard

    search_response = client.get("/api/requests/open?q=Jane", headers=auth_headers)
    assert search_response.status_code == 200
    assert search_response.json()["total"] == 1

    miss_response = client.get("/api/requests/open?q=Alaska", headers=auth_headers)
    assert miss_response.status_code == 200
    assert miss_response.json()["total"] == 0


@pytest.mark.integration
def test_reports_endpoints_return_manifest_and_ledger(client, auth_headers):
    meta_response = client.get("/api/reports/meta", headers=auth_headers)
    assert meta_response.status_code == 200
    assert "workflow_task_groups" in meta_response.json()

    manifest_response = client.get("/api/reports/sales-manifest", headers=auth_headers)
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert "items" in manifest
    assert "total_pages" in manifest

    ledger_response = client.get("/api/reports/supplier-ledger", headers=auth_headers)
    assert ledger_response.status_code == 200
    assert "items" in ledger_response.json()

    funnel_response = client.get("/api/reports/funnel-leak", headers=auth_headers)
    assert funnel_response.status_code == 200
    assert "items" in funnel_response.json()

    scorecard_response = client.get("/api/reports/advisor-scorecard", headers=auth_headers)
    assert scorecard_response.status_code == 200
    assert "items" in scorecard_response.json()

    demographics_response = client.get("/api/reports/passenger-demographics", headers=auth_headers)
    assert demographics_response.status_code == 200
    assert "items" in demographics_response.json()
    assert "advisor_names" in meta_response.json()
    assert "residence_states" in meta_response.json()


@pytest.mark.integration
def test_register_rejected_when_public_registration_disabled(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "allow_public_registration", False)

    response = client.post(
        "/api/auth/register",
        json={
            "username": "blockeduser",
            "email": "blocked@example.com",
            "password": "SecurePass1!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Public registration is disabled."
