from datetime import UTC, date, datetime

from app.constants import (
    REQUEST_STATUS_OPEN,
    TASK_STATUS_DONE,
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
)
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate, RequestWorkflowLive, TravelRequest, User
from app.schemas import RequestTaskUpdate, RequestWorkflowCreate, RequestWorkflowUpdate
from app.security import hash_password
from app.services.workflow_service import start_workflow, update_task, update_workflow
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import set_current_agency_id


def _create_user(db) -> User:
    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="workflow-agent",
        email="workflow-agent@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    db.add(user)
    db.flush()
    return user


def _create_open_request(db, user: User) -> TravelRequest:
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
        updated_at=datetime.now(UTC),
    )
    db.add(request)
    db.flush()
    return request


def _communicate_template(db) -> AgencyWorkflowTemplate:
    return (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
        )
        .one()
    )


def test_start_workflow_does_not_duplicate_tasks_when_template_has_stale_duplicates(db):
    import uuid

    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _create_user(db)
    request = _create_open_request(db, user)
    template = _communicate_template(db)
    expected_keys = {task.task_key for task in template.task_templates if task.task_key}
    for task in template.task_templates:
        if not task.task_key:
            continue
        db.add(
            AgencyTaskTemplate(
                id=str(uuid.uuid4()),
                workflow_template_id=template.id,
                task_title=task.task_title,
                sequence_order=task.sequence_order + 100,
                action_type=task.action_type,
                task_key=task.task_key,
                description=task.description,
            )
        )
    db.commit()

    workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )

    live_keys = [task.task_key for task in workflow.tasks if task.task_key]
    assert len(live_keys) == len(set(live_keys))
    assert set(live_keys) == expected_keys


def test_update_task_auto_completes_workflow_when_all_tasks_done(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _create_user(db)
    request = _create_open_request(db, user)
    template = _communicate_template(db)
    db.commit()

    workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )

    for task in workflow.tasks:
        update_task(
            db,
            request_id=request.id,
            task_id=task.id,
            payload=RequestTaskUpdate(status=TASK_STATUS_DONE),
            current_user=user,
        )

    completed = (
        db.query(RequestWorkflowLive)
        .filter(RequestWorkflowLive.id == workflow.id)
        .one()
    )
    assert completed.status == WORKFLOW_STATUS_COMPLETED
    assert completed.completed_by_id == user.id
    assert completed.ended_at is not None


def test_update_workflow_does_not_auto_start_successor(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _create_user(db)
    request = _create_open_request(db, user)
    template = _communicate_template(db)
    db.commit()

    workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )

    updated = update_workflow(
        db,
        request_id=request.id,
        workflow_id=workflow.id,
        payload=RequestWorkflowUpdate(status=WORKFLOW_STATUS_COMPLETED),
        current_user=user,
    )

    assert updated.status == WORKFLOW_STATUS_COMPLETED
    active_count = (
        db.query(RequestWorkflowLive)
        .filter(
            RequestWorkflowLive.travel_request_id == request.id,
            RequestWorkflowLive.status == WORKFLOW_STATUS_ACTIVE,
        )
        .count()
    )
    assert active_count == 0


def test_task_read_includes_prerequisite_task_keys(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _create_user(db)
    request = _create_open_request(db, user)
    template = _communicate_template(db)
    client_response_template = (
        db.query(AgencyTaskTemplate)
        .filter(
            AgencyTaskTemplate.workflow_template_id == template.id,
            AgencyTaskTemplate.task_key == "client_response",
        )
        .one()
    )
    client_response_template.prerequisite_task_keys = ["send_research_communication"]
    db.commit()

    workflow = start_workflow(
        db,
        request_id=request.id,
        payload=RequestWorkflowCreate(template_id=template.id),
        current_user=user,
    )

    client_response = next(task for task in workflow.tasks if task.task_key == "client_response")
    from app.services.workflow_read import task_to_read

    read_task = task_to_read(client_response)
    assert read_task.prerequisite_task_keys == ["send_research_communication"]
