import pytest
from fastapi import HTTPException

from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.workflow_template_service import transfer_agency_task_to_workflow
from app.tenant_constants import DEFAULT_AGENCY_ID


def test_transfer_agency_task_to_workflow_moves_catalog_task(db):
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
    source_count = (
        db.query(AgencyTaskTemplate)
        .filter(AgencyTaskTemplate.workflow_template_id == source_template_id)
        .count()
    )

    target_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.id != source_template_id,
        )
        .first()
    )
    target_count = len(target_workflow.task_templates)

    source_template, target_template = transfer_agency_task_to_workflow(
        db,
        task_id=task.id,
        target_workflow_template_id=target_workflow.id,
    )

    assert len(source_template.task_templates) == source_count - 1
    assert len(target_template.task_templates) == target_count + 1
    assert any(row.task_key == "research_cruise_options" for row in target_template.task_templates)
    assert all(row.task_key != "research_cruise_options" for row in source_template.task_templates)


def test_transfer_agency_task_rejects_same_workflow(db):
    task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    with pytest.raises(HTTPException) as exc_info:
        transfer_agency_task_to_workflow(
            db,
            task_id=task.id,
            target_workflow_template_id=task.workflow_template_id,
        )
    assert exc_info.value.status_code == 400


def test_transfer_agency_task_renumbers_source_sequence(db):
    source_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    ordered = sorted(source_workflow.task_templates, key=lambda row: row.sequence_order)
    if len(ordered) < 2:
        pytest.skip("Seed needs at least two tasks on a workflow.")

    task = ordered[0]
    target_workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.id != source_workflow.id,
        )
        .first()
    )

    transfer_agency_task_to_workflow(
        db,
        task_id=task.id,
        target_workflow_template_id=target_workflow.id,
    )

    refreshed_source = (
        db.query(AgencyTaskTemplate)
        .filter(AgencyTaskTemplate.workflow_template_id == source_workflow.id)
        .order_by(AgencyTaskTemplate.sequence_order.asc())
        .all()
    )
    assert [row.sequence_order for row in refreshed_source] == list(range(1, len(refreshed_source) + 1))


def test_transfer_agency_task_inserts_at_position(db):
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
    target_tasks_before = sorted(target_workflow.task_templates, key=lambda row: row.sequence_order)
    if not target_tasks_before:
        pytest.skip("Target workflow needs at least one task to test insert position.")

    _, target_template = transfer_agency_task_to_workflow(
        db,
        task_id=task.id,
        target_workflow_template_id=target_workflow.id,
        sequence_order=1,
    )

    ordered = sorted(target_template.task_templates, key=lambda row: row.sequence_order)
    assert ordered[0].task_key == "research_cruise_options"
    assert ordered[1].id == target_tasks_before[0].id
