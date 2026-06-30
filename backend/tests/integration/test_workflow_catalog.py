import pytest


@pytest.mark.integration
def test_agency_task_catalog_requires_super_user(client, db):
    from app.models import User
    from app.security import hash_password
    from app.tenant_constants import DEFAULT_AGENCY_ID
    from app.tenant_roles import USER_ROLE_TENANT_AGENT

    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="workflowagent",
        email="workflowagent@example.com",
        password_hash=hash_password("TestPassword1!"),
        role=USER_ROLE_TENANT_AGENT,
    )
    db.add(agent)
    db.commit()

    login = client.post(
        "/api/auth/login",
        json={
            "organization_handle": "default",
            "username": agent.username,
            "password": "TestPassword1!",
        },
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/api/agency-task-catalog", headers=headers)
    assert response.status_code == 403


@pytest.mark.integration
def test_agency_task_catalog_returns_built_in_tasks(client, auth_headers):
    response = client.get("/api/agency-task-catalog", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 12
    keys = {item["task_key"] for item in payload}
    assert "research_cruise_options" in keys
    assert all(item["action_type"] == "custom_panel" for item in payload)


@pytest.mark.integration
def test_agency_task_availability_after_seed(client, auth_headers):
    response = client.get("/api/agency-task-catalog/availability", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["available_count"] == 0
    assert len(payload["placed_task_keys"]) == 12
    assert payload["available_tasks"] == []


@pytest.mark.integration
def test_create_catalog_task_rejects_duplicate(client, auth_headers, db):
    from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
    from app.tenant_constants import DEFAULT_AGENCY_ID

    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    response = client.post(
        f"/api/agency-workflow-templates/{workflow.id}/catalog-tasks",
        headers=auth_headers,
        json={"task_key": "research_cruise_options"},
    )
    assert response.status_code == 400
    assert "already on a playbook" in response.json()["detail"]


@pytest.mark.integration
def test_create_catalog_task_after_removal(client, auth_headers, db):
    from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
    from app.tenant_constants import DEFAULT_AGENCY_ID

    task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyTaskTemplate.task_key == "research_cruise_options",
        )
        .one()
    )
    original_template_id = task.workflow_template_id
    db.delete(task)
    db.commit()

    other_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.id != original_template_id,
        )
        .first()
    )

    response = client.post(
        f"/api/agency-workflow-templates/{other_workflow.id}/catalog-tasks",
        headers=auth_headers,
        json={"task_key": "research_cruise_options"},
    )
    assert response.status_code == 201
    body = response.json()
    added = next(
        task_row
        for task_row in body["task_templates"]
        if task_row["task_key"] == "research_cruise_options"
    )
    assert added["task_title"] == "Research cruise options"

    availability = client.get("/api/agency-task-catalog/availability", headers=auth_headers)
    assert availability.json()["available_count"] == 0
