import pytest
from fastapi import HTTPException

from app.constants import TASK_ACTION_CUSTOM_PANEL
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.workflow_task_catalog_service import (
    assert_task_key_available_for_agency,
    build_system_task_catalog,
    get_agency_task_availability,
    get_catalog_item,
)
from app.services.workflow_template_service import create_agency_task_from_catalog
from app.tenant_constants import DEFAULT_AGENCY_ID


def test_build_system_task_catalog_has_unique_sorted_keys():
    catalog = build_system_task_catalog()
    keys = [item["task_key"] for item in catalog]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))
    assert len(catalog) == 12
    assert all(item["action_type"] == TASK_ACTION_CUSTOM_PANEL for item in catalog)


def test_get_catalog_item_returns_known_task():
    item = get_catalog_item("research_cruise_options")
    assert item is not None
    assert item["task_title"] == "Research cruise options"


def test_get_agency_task_availability_after_seed(db):
    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert payload["available_count"] == 0
    assert len(payload["placed_task_keys"]) == 12
    assert payload["available_tasks"] == []


def test_availability_frees_removed_task(db):
    task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyTaskTemplate.task_key == "research_cruise_options",
        )
        .one()
    )
    db.delete(task)
    db.commit()

    payload = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert payload["available_count"] == 1
    assert payload["available_tasks"][0]["task_key"] == "research_cruise_options"
    assert "research_cruise_options" not in payload["placed_task_keys"]


def test_assert_task_key_available_rejects_duplicate(db):
    with pytest.raises(HTTPException) as exc_info:
        assert_task_key_available_for_agency(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            task_key="research_cruise_options",
        )
    assert exc_info.value.status_code == 400


def test_create_agency_task_from_catalog_rejects_duplicate(db):
    workflow = (
        db.query(AgencyWorkflowTemplate)
        .filter(AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID)
        .first()
    )
    with pytest.raises(HTTPException) as exc_info:
        create_agency_task_from_catalog(
            db,
            template_id=workflow.id,
            task_key="research_cruise_options",
        )
    assert exc_info.value.status_code == 400


def test_create_agency_task_from_catalog_adds_freed_task(db):
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
    created = create_agency_task_from_catalog(
        db,
        template_id=other_workflow.id,
        task_key="research_cruise_options",
    )
    assert created.task_key == "research_cruise_options"
    assert created.workflow_template_id == other_workflow.id

    with pytest.raises(HTTPException):
        create_agency_task_from_catalog(
            db,
            template_id=original_template_id,
            task_key="research_cruise_options",
        )
