import pytest


@pytest.mark.integration
def test_transfer_task_between_workflows(client, auth_headers, db):
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
    source_template_id = task.workflow_template_id

    target_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.id != source_template_id,
        )
        .first()
    )
    original_target_count = len(target_workflow.task_templates)

    response = client.patch(
        f"/api/agency-workflow-templates/tasks/{task.id}/move",
        headers=auth_headers,
        json={"target_workflow_template_id": target_workflow.id},
    )
    assert response.status_code == 200
    body = response.json()
    source_tasks = body["source_workflow_template"]["task_templates"]
    target_tasks = body["target_workflow_template"]["task_templates"]
    assert all(row["task_key"] != "research_cruise_options" for row in source_tasks)
    moved = next(row for row in target_tasks if row["task_key"] == "research_cruise_options")
    assert moved["task_title"] == "Research cruise options"
    assert len(target_tasks) == original_target_count + 1


@pytest.mark.integration
def test_transfer_task_rejects_same_workflow(client, auth_headers, db):
    from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
    from app.tenant_constants import DEFAULT_AGENCY_ID

    task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    response = client.patch(
        f"/api/agency-workflow-templates/tasks/{task.id}/move",
        headers=auth_headers,
        json={"target_workflow_template_id": task.workflow_template_id},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Task is already on that workflow."


@pytest.mark.integration
def test_transfer_task_inserts_at_sequence_position(client, auth_headers, db):
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
    source_template_id = task.workflow_template_id

    target_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.id != source_template_id,
        )
        .first()
    )
    first_target_task = min(target_workflow.task_templates, key=lambda row: row.sequence_order, default=None)
    if first_target_task is None:
        pytest.skip("Target workflow needs at least one task to test insert position.")

    response = client.patch(
        f"/api/agency-workflow-templates/tasks/{task.id}/move",
        headers=auth_headers,
        json={
            "target_workflow_template_id": target_workflow.id,
            "sequence_order": 1,
        },
    )
    assert response.status_code == 200
    target_tasks = sorted(
        response.json()["target_workflow_template"]["task_templates"],
        key=lambda row: row["sequence_order"],
    )
    assert target_tasks[0]["task_key"] == "research_cruise_options"
    assert target_tasks[1]["id"] == first_target_task.id
