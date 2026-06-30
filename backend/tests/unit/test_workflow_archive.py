from datetime import date

import pytest
from fastapi import HTTPException

from app.constants import (
    REQUEST_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_TERMINATED,
    WORKFLOW_TYPE_RESEARCH,
)
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate, RequestWorkflowLive, TravelRequest, User
from app.schemas import RequestWorkflowCreate
from app.security import hash_password
from app.services.agency_custom_task_service import (
    create_agency_custom_task_definition,
    create_agency_task_from_custom_definition,
)
from app.services.workflow_task_catalog_service import get_agency_task_availability
from app.services.workflow_template_seed import seed_agency_workflow_templates
from app.services.workflow_service import get_active_workflow, start_workflow
from app.services.workflow_template_service import (
    archive_agency_workflow_template,
    create_agency_workflow_template,
    list_agency_workflow_templates,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import set_current_agency_id


def _user(db) -> User:
    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="archive-admin",
        email="archive-admin@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    db.add(user)
    db.flush()
    return user


def _open_request(db, user: User) -> TravelRequest:
    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        close_reason=None,
        created_by=user,
        updated_by=user,
    )
    db.add(request)
    db.flush()
    return request


def _research_template(db) -> AgencyWorkflowTemplate:
    return (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
        )
        .one()
    )


def test_archive_custom_workflow_releases_tasks(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    workflow = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Disposable custom workflow",
    )
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Disposable archive task",
    )
    create_agency_task_from_custom_definition(
        db,
        template_id=workflow.id,
        task_key=definition.task_key,
    )

    archive_agency_workflow_template(db, template_id=workflow.id, current_user=user)

    db.refresh(workflow)
    assert workflow.archived_at is not None
    assert workflow.task_templates == []
    assert workflow.id not in {template.id for template in list_agency_workflow_templates(db, agency_id=DEFAULT_AGENCY_ID)}

    availability = get_agency_task_availability(db, agency_id=DEFAULT_AGENCY_ID)
    assert definition.task_key not in availability["placed_task_keys"]


def test_archive_terminates_active_request_workflows(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    request = _open_request(db, user)
    template = _research_template(db)
    db.commit()

    live_workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )
    assert live_workflow.status == WORKFLOW_STATUS_ACTIVE
    assert get_active_workflow(db, request.id) is not None

    archive_agency_workflow_template(db, template_id=template.id, current_user=user)

    terminated = db.get(RequestWorkflowLive, live_workflow.id)
    assert terminated is not None
    assert terminated.status == WORKFLOW_STATUS_TERMINATED
    assert terminated.ended_at is not None
    assert terminated.completed_by_id == user.id
    assert get_active_workflow(db, request.id) is None


def test_archive_leaves_completed_request_workflows_unchanged(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    request = _open_request(db, user)
    template = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Already completed workflow template",
    )
    definition = create_agency_custom_task_definition(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        task_title="Single archive task",
    )
    create_agency_task_from_custom_definition(
        db,
        template_id=template.id,
        task_key=definition.task_key,
    )
    db.commit()

    live_workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )
    live_workflow.status = WORKFLOW_STATUS_COMPLETED
    live_workflow.completed_by_id = user.id
    live_workflow.ended_at = live_workflow.started_at
    db.commit()

    archive_agency_workflow_template(db, template_id=template.id, current_user=user)

    completed = db.get(RequestWorkflowLive, live_workflow.id)
    assert completed is not None
    assert completed.status == WORKFLOW_STATUS_COMPLETED


def test_archive_recommended_workflow_hides_without_resurrecting(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    research = _research_template(db)
    original_id = research.id
    placed_before = (
        db.query(AgencyTaskTemplate)
        .filter(AgencyTaskTemplate.workflow_template_id == research.id)
        .count()
    )
    assert placed_before > 0

    archive_agency_workflow_template(db, template_id=research.id, current_user=user)

    db.refresh(research)
    assert research.archived_at is not None
    assert research.task_templates == []

    listed = list_agency_workflow_templates(db, agency_id=DEFAULT_AGENCY_ID)
    assert original_id not in {template.id for template in listed}

    seed_agency_workflow_templates(db, agency_id=DEFAULT_AGENCY_ID)
    db.commit()

    listed_after_seed = list_agency_workflow_templates(db, agency_id=DEFAULT_AGENCY_ID)
    assert original_id not in {template.id for template in listed_after_seed}

    archived_row = db.get(AgencyWorkflowTemplate, original_id)
    assert archived_row is not None
    assert archived_row.archived_at is not None


def test_archive_workflow_is_idempotent_guard(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    workflow = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Archive once",
    )

    archive_agency_workflow_template(db, template_id=workflow.id, current_user=user)

    with pytest.raises(HTTPException) as exc_info:
        archive_agency_workflow_template(db, template_id=workflow.id, current_user=user)
    assert exc_info.value.status_code == 400
