import pytest

from app.constants import WORKFLOW_TYPE_RESEARCH
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.workflow_template_service import create_agency_workflow_template
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.workflow_helpers import WORKFLOW_TASK_TEMPLATES


@pytest.mark.integration
def test_reset_recommended_workflow_api(client, auth_headers, db):
    template = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
        )
        .one()
    )
    template.workflow_name = "Mutated research"
    db.commit()

    response = client.post(
        f"/api/agency-workflow-templates/{template.id}/reset-to-default",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "restored" in body["message"].lower()
    assert body["template"]["workflow_name"] == "Research"
    assert len(body["template"]["task_templates"]) == len(WORKFLOW_TASK_TEMPLATES[WORKFLOW_TYPE_RESEARCH])


@pytest.mark.integration
def test_reset_custom_workflow_api_rejected(client, auth_headers, db):
    custom = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Empty custom workflow",
    )

    response = client.post(
        f"/api/agency-workflow-templates/{custom.id}/reset-to-default",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.integration
def test_patch_task_sequence_order_api(client, auth_headers, db):
    task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
            AgencyTaskTemplate.task_key == "create_proposed_cruises",
        )
        .one()
    )

    response = client.patch(
        f"/api/agency-workflow-templates/tasks/{task.id}",
        headers=auth_headers,
        json={"sequence_order": 1},
    )
    assert response.status_code == 200
    ordered = sorted(response.json()["task_templates"], key=lambda row: row["sequence_order"])
    assert ordered[0]["task_key"] == "create_proposed_cruises"


@pytest.mark.integration
def test_workflow_templates_include_task_metadata(client, auth_headers, db):
    custom = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Picker empty custom",
    )
    db.commit()

    response = client.get("/api/workflow-templates", headers=auth_headers)
    assert response.status_code == 200
    templates = response.json()
    research = next(row for row in templates if row["workflow_type"] == WORKFLOW_TYPE_RESEARCH)
    empty_custom = next(row for row in templates if row["id"] == custom.id)

    assert research["task_count"] > 0
    assert research["is_recommended"] is True
    assert empty_custom["task_count"] == 0
    assert empty_custom["is_recommended"] is False
