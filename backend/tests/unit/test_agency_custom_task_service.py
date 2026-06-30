import pytest
from fastapi import HTTPException

from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.agency_custom_task_service import (
    create_agency_custom_task_definition,
    create_agency_task_from_custom_definition,
    delete_agency_custom_task_definition,
    update_agency_custom_task_definition,
)
from app.services.workflow_task_catalog_service import get_agency_task_availability
from app.tenant_constants import DEFAULT_AGENCY_ID


def test_create_custom_task_definition_generates_task_key(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Confirm insurance",
        description="Ask client about travel insurance.",
    )
    assert definition.task_key.startswith("custom_")
    assert definition.task_title == "Confirm insurance"
    assert definition.description == "Ask client about travel insurance."


def test_availability_includes_unplaced_custom_definition(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Follow up on documents",
    )
    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert payload["available_count"] >= 1
    assert any(item["task_key"] == definition.task_key for item in payload["available_custom_tasks"])


def test_create_agency_task_from_custom_definition_places_task(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Send welcome packet",
    )
    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    created = create_agency_task_from_custom_definition(
        db,
        template_id=workflow.id,
        task_key=definition.task_key,
    )
    assert created.task_key == definition.task_key
    assert created.task_title == "Send welcome packet"

    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert definition.task_key in payload["placed_task_keys"]
    assert definition.task_key not in [item["task_key"] for item in payload["available_custom_tasks"]]


def test_create_agency_task_from_custom_definition_inserts_at_sequence(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Insert at start",
    )
    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    first_task = (
        db.query(AgencyTaskTemplate)
        .filter(AgencyTaskTemplate.workflow_template_id == workflow.id)
        .order_by(AgencyTaskTemplate.sequence_order.asc())
        .first()
    )

    created = create_agency_task_from_custom_definition(
        db,
        template_id=workflow.id,
        task_key=definition.task_key,
        sequence_order=1,
    )
    db.refresh(first_task)

    assert created.sequence_order == 1
    assert first_task.sequence_order == 2


def test_update_custom_definition_syncs_placed_task(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Initial title",
        description="Initial description.",
    )
    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    placed = create_agency_task_from_custom_definition(
        db,
        template_id=workflow.id,
        task_key=definition.task_key,
    )

    updated = update_agency_custom_task_definition(
        db,
        definition_id=definition.id,
        task_title="Updated title",
        description="Updated description.",
    )
    db.refresh(placed)

    assert updated.task_title == "Updated title"
    assert updated.description == "Updated description."
    assert placed.task_title == "Updated title"
    assert placed.description == "Updated description."


def test_delete_custom_definition_removes_placed_task(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Delete guard",
    )
    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    create_agency_task_from_custom_definition(
        db,
        template_id=workflow.id,
        task_key=definition.task_key,
    )

    delete_agency_custom_task_definition(db, definition_id=definition.id)

    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert definition.task_key not in payload["placed_task_keys"]
    assert definition.task_key not in [item["task_key"] for item in payload["available_custom_tasks"]]


def test_delete_custom_definition_when_unplaced(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Disposable task",
    )
    delete_agency_custom_task_definition(db, definition_id=definition.id)
    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert definition.task_key not in [item["task_key"] for item in payload["available_custom_tasks"]]


def test_create_agency_task_from_custom_definition_rejects_duplicate_placement(db):
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="One workflow only",
    )
    workflows = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .limit(2)
        .all()
    )
    create_agency_task_from_custom_definition(
        db,
        template_id=workflows[0].id,
        task_key=definition.task_key,
    )

    with pytest.raises(HTTPException) as exc_info:
        create_agency_task_from_custom_definition(
            db,
            template_id=workflows[1].id,
            task_key=definition.task_key,
        )
    assert exc_info.value.status_code == 400
