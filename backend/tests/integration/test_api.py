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
        "/api/public/register",
        json={
            "agency_name": "New Agent Travel",
            "admin_name": "New Agent",
            "admin_email": "newagent@example.com",
            "password": "SecurePass1!",
        },
    )
    assert register_response.status_code == 201, register_response.text
    auth_payload = register_response.json()
    assert auth_payload["user"]["email"] == "newagent@example.com"
    assert "access_token" in auth_payload

    login_response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "new-agent-travel",
            "username": auth_payload["user"]["username"],
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
    assert payload["page_size"] == 10
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
    assert payload["page_size"] == 10
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
def test_marketing_campaigns_crud_and_lead_attribution(client, auth_headers, sample_request_payload):
    create_campaign = client.post(
        "/api/marketing-campaigns",
        headers=auth_headers,
        json={
            "campaign_name": "Summer Facebook Push",
            "campaign_type": "Facebook/Instagram",
            "monthly_spend": 450,
            "start_date": "2026-04-01",
            "end_date": None,
        },
    )
    assert create_campaign.status_code == 201, create_campaign.text
    campaign_id = create_campaign.json()["id"]

    list_response = client.get("/api/marketing-campaigns?timeframe=all", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == campaign_id for item in list_response.json())

    request_payload = {
        **sample_request_payload,
        "lead_source": "Marketing Campaign",
        "marketing_campaign_id": campaign_id,
    }
    create_request = client.post("/api/requests", headers=auth_headers, json=request_payload)
    assert create_request.status_code == 201, create_request.text
    assert create_request.json()["marketing_campaign_id"] == campaign_id

    delete_response = client.delete(f"/api/marketing-campaigns/{campaign_id}", headers=auth_headers)
    assert delete_response.status_code == 204


@pytest.mark.integration
def test_marketing_campaign_summary_reads_cached_rollups(client, auth_headers, sample_request_payload):
    create_campaign = client.post(
        "/api/marketing-campaigns",
        headers=auth_headers,
        json={
            "campaign_name": "Summary Campaign",
            "campaign_type": "Email Newsletter",
            "monthly_spend": 1200,
            "start_date": "2026-01-01",
            "end_date": None,
        },
    )
    assert create_campaign.status_code == 201, create_campaign.text

    summary_response = client.get("/api/marketing-campaigns/summary", headers=auth_headers)
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert "active_monthly_budget" in summary
    assert "top_roi_campaign_name" in summary
    assert "top_roi_percent" in summary
    assert "total_attributed_volume" in summary


@pytest.mark.integration
def test_legacy_register_endpoint_is_disabled(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "blockeduser",
            "email": "blocked@example.com",
            "password": "SecurePass1!",
        },
    )

    assert response.status_code == 410
    assert "public/register" in response.json()["detail"].lower()
