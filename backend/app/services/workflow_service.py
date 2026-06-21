from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.audit_helpers import (
    TRAVEL_REQUEST_AUDIT_FIELDS,
    apply_updates,
    collect_field_changes,
    record_travel_request_field_changes,
)
from app.constants import (
    CLOSE_REASONS,
    REQUEST_STATUS_CLOSED,
    TASK_STATUS_DONE,
    TASK_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_CANCELLED,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_TYPE_ENTER_TRIP_CRM,
    WORKFLOW_TYPE_RESEARCH,
)
from app.models import RequestTask, RequestWorkflow, TravelRequest, User
from app.schemas import RequestTaskUpdate, RequestWorkflowCreate, RequestWorkflowUpdate, WorkflowTemplateRead
from app.services.agency_service import assert_child_belongs_to_request, require_record_for_agency
from app.services.request_service import get_open_request, touch_request
from app.tenant_context import require_current_agency_id
from app.workflow_helpers import (
    WORKFLOW_DEFINITIONS,
    ensure_follow_up_due_date,
    get_successor_workflow_type,
    get_task_templates,
    record_follow_up_reached_out,
    schedule_follow_up_due_date,
    TASK_KEY_SEND_RESEARCH_COMMUNICATION,
)


def load_workflow(db: Session, workflow_id: int) -> RequestWorkflow:
    return (
        db.query(RequestWorkflow)
        .options(
            joinedload(RequestWorkflow.started_by),
            joinedload(RequestWorkflow.completed_by),
            joinedload(RequestWorkflow.tasks).joinedload(RequestTask.completed_by),
        )
        .filter(RequestWorkflow.id == workflow_id)
        .one()
    )


def get_active_workflow(db: Session, request_id: int) -> RequestWorkflow | None:
    return (
        db.query(RequestWorkflow)
        .filter(
            RequestWorkflow.travel_request_id == request_id,
            RequestWorkflow.status == WORKFLOW_STATUS_ACTIVE,
        )
        .first()
    )


def create_request_workflow(
    db: Session,
    *,
    request: TravelRequest,
    workflow_type: str,
    current_user: User,
    parent_workflow_id: int | None = None,
) -> RequestWorkflow:
    if parent_workflow_id is not None:
        parent = db.get(RequestWorkflow, parent_workflow_id)
        require_record_for_agency(parent, agency_id=request.agency_id)
        assert_child_belongs_to_request(
            child_agency_id=parent.agency_id,
            child_travel_request_id=parent.travel_request_id,
            request_id=request.id,
            agency_id=request.agency_id,
        )

    workflow = RequestWorkflow(
        agency_id=request.agency_id,
        travel_request_id=request.id,
        workflow_type=workflow_type,
        status=WORKFLOW_STATUS_ACTIVE,
        parent_workflow_id=parent_workflow_id,
        started_by_id=current_user.id,
    )
    db.add(workflow)
    db.flush()

    for template in get_task_templates(workflow_type):
        db.add(
            RequestTask(
                agency_id=request.agency_id,
                request_workflow_id=workflow.id,
                travel_request_id=request.id,
                task_key=template.task_key,
                title=template.title,
                description=template.description,
                status=TASK_STATUS_OPEN,
                sort_order=template.sort_order,
            )
        )

    return workflow


def list_workflow_templates() -> list[WorkflowTemplateRead]:
    return [
        WorkflowTemplateRead(
            workflow_type=workflow_type,
            name=definition["name"],
            description=definition["description"],
        )
        for workflow_type, definition in WORKFLOW_DEFINITIONS.items()
    ]


def start_workflow(
    db: Session,
    *,
    request_id: int,
    payload: RequestWorkflowCreate,
    current_user: User,
) -> RequestWorkflow:
    request = get_open_request(db, request_id)
    if get_active_workflow(db, request_id) is not None:
        raise HTTPException(
            status_code=400,
            detail="This request already has an active workflow. Complete or cancel it before starting another.",
        )

    if payload.parent_workflow_id is not None:
        parent = db.get(RequestWorkflow, payload.parent_workflow_id)
        require_record_for_agency(parent, agency_id=request.agency_id)
        assert_child_belongs_to_request(
            child_agency_id=parent.agency_id,
            child_travel_request_id=parent.travel_request_id,
            request_id=request_id,
            agency_id=request.agency_id,
        )

    workflow = create_request_workflow(
        db,
        request=request,
        workflow_type=payload.workflow_type,
        current_user=current_user,
        parent_workflow_id=payload.parent_workflow_id,
    )
    touch_request(request, current_user)
    db.commit()
    return load_workflow(db, workflow.id)


def update_workflow(
    db: Session,
    *,
    request_id: int,
    workflow_id: int,
    payload: RequestWorkflowUpdate,
    current_user: User,
) -> RequestWorkflow:
    request = get_open_request(db, request_id)
    workflow = db.get(RequestWorkflow, workflow_id)
    require_record_for_agency(workflow, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=workflow.agency_id,
        child_travel_request_id=workflow.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    just_completed = False
    if payload.status is not None and payload.status != workflow.status:
        if payload.status in {WORKFLOW_STATUS_COMPLETED, WORKFLOW_STATUS_CANCELLED}:
            workflow.status = payload.status
            workflow.completed_by_id = current_user.id
            workflow.completed_at = datetime.now(UTC).replace(tzinfo=None)
            just_completed = payload.status == WORKFLOW_STATUS_COMPLETED
        else:
            workflow.status = payload.status

    successor_workflow: RequestWorkflow | None = None
    if just_completed and workflow.workflow_type == WORKFLOW_TYPE_RESEARCH:
        successor_type = get_successor_workflow_type(workflow.workflow_type)
        if successor_type is not None:
            db.flush()
            successor_workflow = create_request_workflow(
                db,
                request=request,
                workflow_type=successor_type,
                current_user=current_user,
                parent_workflow_id=workflow.id,
            )
    elif just_completed and workflow.workflow_type == WORKFLOW_TYPE_ENTER_TRIP_CRM:
        if not payload.close_reason:
            raise HTTPException(
                status_code=400,
                detail="Select a close reason before completing this workflow.",
            )
        if payload.close_reason not in CLOSE_REASONS:
            raise HTTPException(status_code=400, detail="Invalid close reason selected.")
        close_updates = {
            "status": REQUEST_STATUS_CLOSED,
            "close_reason": payload.close_reason,
        }
        request_changes = collect_field_changes(request, close_updates, TRAVEL_REQUEST_AUDIT_FIELDS)
        record_travel_request_field_changes(db, request, request_changes, current_user)
        apply_updates(request, close_updates)

    touch_request(request, current_user)
    db.commit()
    if successor_workflow is not None:
        return load_workflow(db, successor_workflow.id)
    return load_workflow(db, workflow.id)


def update_task(
    db: Session,
    *,
    request_id: int,
    task_id: int,
    payload: RequestTaskUpdate,
    current_user: User,
) -> RequestWorkflow:
    request = get_open_request(db, request_id)
    task = db.get(RequestTask, task_id)
    require_record_for_agency(task, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=task.agency_id,
        child_travel_request_id=task.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    workflow = load_workflow(db, task.request_workflow_id)
    if workflow.status != WORKFLOW_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="Tasks can only be updated on active workflows.")

    if payload.status is not None:
        task.status = payload.status
        if payload.status == TASK_STATUS_DONE:
            task.completed_at = datetime.now(UTC).replace(tzinfo=None)
            task.completed_by_id = current_user.id
            if task.task_key == TASK_KEY_SEND_RESEARCH_COMMUNICATION:
                schedule_follow_up_due_date(workflow, task.completed_at)
        elif payload.status == TASK_STATUS_OPEN:
            task.completed_at = None
            task.completed_by_id = None

    payload_data = payload.model_dump(exclude_unset=True)
    if payload_data.get("reached_out"):
        try:
            record_follow_up_reached_out(task, now=datetime.now(UTC).replace(tzinfo=None))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    if "due_at" in payload_data:
        task.due_at = payload.due_at

    if "result" in payload_data:
        task.result = payload.result

    ensure_follow_up_due_date(workflow)

    touch_request(request, current_user)
    db.commit()
    return load_workflow(db, workflow.id)
