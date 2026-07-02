from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.constants import (
    TASK_STATUS_DONE,
    TASK_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
    WORKFLOW_STATUS_COMPLETED,
    WORKFLOW_STATUS_TERMINATED,
    WORKFLOW_TYPE_ENTER_TRIP_CRM,
)
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate, RequestTaskLive, RequestWorkflowLive, TravelRequest, User
from app.schemas import (
    RequestTaskUpdate,
    RequestWorkflowCreate,
    RequestWorkflowUpdate,
    WorkflowTemplateRead,
)
from app.services.agency_service import assert_child_belongs_to_request, require_record_for_agency
from app.services.request_service import get_open_request, touch_request
from app.services.workflow_template_seed import seed_agency_workflow_templates
from app.tenant_context import require_current_agency_id
from app.workflow_helpers import (
    apply_task_completion_side_effects,
    ensure_follow_up_due_date,
    record_follow_up_reached_out,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def terminate_active_live_workflows_for_template(
    db: Session,
    *,
    template_id: str,
    agency_id: str,
    current_user: User,
) -> int:
    """End in-flight request workflows that were started from this agency template."""
    from app.services.request_service import touch_request

    now = datetime.now(UTC).replace(tzinfo=None)
    active_workflows = (
        db.query(RequestWorkflowLive)
        .options(joinedload(RequestWorkflowLive.travel_request))
        .filter(
            RequestWorkflowLive.template_id == template_id,
            RequestWorkflowLive.agency_id == agency_id,
            RequestWorkflowLive.status == WORKFLOW_STATUS_ACTIVE,
        )
        .all()
    )

    touched_request_ids: set[int] = set()
    for workflow in active_workflows:
        workflow.status = WORKFLOW_STATUS_TERMINATED
        workflow.ended_at = now
        workflow.completed_by_id = current_user.id
        if workflow.travel_request_id not in touched_request_ids:
            touch_request(workflow.travel_request, current_user)
            touched_request_ids.add(workflow.travel_request_id)

    return len(active_workflows)


def load_workflow(db: Session, workflow_id: str) -> RequestWorkflowLive:
    workflow = (
        db.query(RequestWorkflowLive)
        .options(
            joinedload(RequestWorkflowLive.started_by),
            joinedload(RequestWorkflowLive.completed_by),
            joinedload(RequestWorkflowLive.tasks).joinedload(RequestTaskLive.completed_by),
            joinedload(RequestWorkflowLive.tasks).joinedload(RequestTaskLive.template_task),
        )
        .filter(RequestWorkflowLive.id == workflow_id)
        .one()
    )
    return workflow


def get_active_workflow(db: Session, request_id: int) -> RequestWorkflowLive | None:
    return (
        db.query(RequestWorkflowLive)
        .filter(
            RequestWorkflowLive.travel_request_id == request_id,
            RequestWorkflowLive.status == WORKFLOW_STATUS_ACTIVE,
        )
        .first()
    )


def _resolve_template(
    db: Session,
    *,
    agency_id: str,
    template_id: str | None = None,
    workflow_type: str | None = None,
) -> AgencyWorkflowTemplate:
    seed_agency_workflow_templates(db, agency_id)
    query = db.query(AgencyWorkflowTemplate).options(joinedload(AgencyWorkflowTemplate.task_templates))
    query = query.filter(AgencyWorkflowTemplate.archived_at.is_(None))
    if template_id is not None:
        template = query.filter(AgencyWorkflowTemplate.id == template_id).first()
    elif workflow_type is not None:
        template = query.filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.workflow_type_key == workflow_type,
        ).first()
    else:
        raise HTTPException(status_code=400, detail="Select a workflow.")

    if template is None or not template.task_templates:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    require_record_for_agency(template, agency_id=agency_id)
    return template


def _snapshot_live_workflow(
    db: Session,
    *,
    request: TravelRequest,
    template: AgencyWorkflowTemplate,
    current_user: User,
    parent_workflow_live_id: str | None = None,
) -> RequestWorkflowLive:
    workflow = RequestWorkflowLive(
        id=_new_id(),
        agency_id=request.agency_id,
        travel_request_id=request.id,
        template_id=template.id,
        workflow_name=template.workflow_name,
        workflow_type_key=template.workflow_type_key,
        status=WORKFLOW_STATUS_ACTIVE,
        parent_workflow_live_id=parent_workflow_live_id,
        started_by_id=current_user.id,
    )
    db.add(workflow)
    db.flush()

    for task_template in sorted(template.task_templates, key=lambda row: row.sequence_order):
        db.add(
            RequestTaskLive(
                id=_new_id(),
                agency_id=request.agency_id,
                request_workflow_live_id=workflow.id,
                travel_request_id=request.id,
                template_task_id=task_template.id,
                task_key=task_template.task_key,
                task_title=task_template.task_title,
                description=task_template.description,
                sequence_order=task_template.sequence_order,
                action_type=task_template.action_type,
                target_field=task_template.target_field,
                status=TASK_STATUS_OPEN,
                is_completed=False,
            )
        )

    return workflow


def list_workflow_templates(db: Session, *, agency_id: str) -> list[WorkflowTemplateRead]:
    seed_agency_workflow_templates(db, agency_id)
    db.flush()
    templates = (
        db.query(AgencyWorkflowTemplate)
        .options(joinedload(AgencyWorkflowTemplate.task_templates))
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
        )
        .order_by(AgencyWorkflowTemplate.workflow_name.asc())
        .all()
    )
    return [
        WorkflowTemplateRead(
            id=template.id,
            workflow_type=template.workflow_type_key or template.id,
            name=template.workflow_name,
            description=template.description or "",
            task_count=len(template.task_templates),
            is_recommended=template.workflow_type_key is not None,
        )
        for template in templates
    ]


def start_workflow(
    db: Session,
    *,
    request_id: int,
    payload: RequestWorkflowCreate,
    current_user: User,
) -> RequestWorkflowLive:
    request = get_open_request(db, request_id)
    if get_active_workflow(db, request_id) is not None:
        raise HTTPException(
            status_code=400,
            detail="This request already has an active workflow. Complete or terminate it before starting another.",
        )

    parent_workflow_live_id = payload.parent_workflow_id
    if parent_workflow_live_id is not None:
        parent = db.get(RequestWorkflowLive, parent_workflow_live_id)
        require_record_for_agency(parent, agency_id=request.agency_id)
        assert_child_belongs_to_request(
            child_agency_id=parent.agency_id,
            child_travel_request_id=parent.travel_request_id,
            request_id=request_id,
            agency_id=request.agency_id,
        )

    template = _resolve_template(
        db,
        agency_id=request.agency_id,
        template_id=payload.template_id,
        workflow_type=payload.workflow_type,
    )
    workflow = _snapshot_live_workflow(
        db,
        request=request,
        template=template,
        current_user=current_user,
        parent_workflow_live_id=parent_workflow_live_id,
    )
    if template.workflow_type_key == WORKFLOW_TYPE_ENTER_TRIP_CRM:
        from app.services.tc_workflow_service import sync_master_terms_tasks_for_request

        sync_master_terms_tasks_for_request(db, travel_request_id=request.id)
    touch_request(request, current_user)
    db.commit()
    return load_workflow(db, workflow.id)


def update_workflow(
    db: Session,
    *,
    request_id: int,
    workflow_id: str,
    payload: RequestWorkflowUpdate,
    current_user: User,
) -> RequestWorkflowLive:
    request = get_open_request(db, request_id)
    workflow = db.get(RequestWorkflowLive, workflow_id)
    require_record_for_agency(workflow, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=workflow.agency_id,
        child_travel_request_id=workflow.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    if payload.status is not None and payload.status != workflow.status:
        if payload.status in {WORKFLOW_STATUS_COMPLETED, WORKFLOW_STATUS_TERMINATED, "Cancelled"}:
            mapped_status = WORKFLOW_STATUS_TERMINATED if payload.status in {"Cancelled", WORKFLOW_STATUS_TERMINATED} else WORKFLOW_STATUS_COMPLETED
            workflow.status = mapped_status
            workflow.completed_by_id = current_user.id
            workflow.ended_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            workflow.status = payload.status

    touch_request(request, current_user)
    db.commit()
    return load_workflow(db, workflow.id)


def _maybe_auto_complete_workflow(workflow: RequestWorkflowLive, current_user: User) -> None:
    if workflow.status != WORKFLOW_STATUS_ACTIVE or not workflow.tasks:
        return
    if not all(task.status == TASK_STATUS_DONE for task in workflow.tasks):
        return
    workflow.status = WORKFLOW_STATUS_COMPLETED
    workflow.completed_by_id = current_user.id
    workflow.ended_at = datetime.now(UTC).replace(tzinfo=None)


def _apply_task_status(task: RequestTaskLive, status: str, current_user: User) -> None:
    task.status = status
    task.is_completed = status == TASK_STATUS_DONE
    if status == TASK_STATUS_DONE:
        task.completed_at = datetime.now(UTC).replace(tzinfo=None)
        task.completed_by_id = current_user.id
    elif status == TASK_STATUS_OPEN:
        task.completed_at = None
        task.completed_by_id = None


def update_task(
    db: Session,
    *,
    request_id: int,
    task_id: str,
    payload: RequestTaskUpdate,
    current_user: User,
) -> RequestWorkflowLive:
    request = get_open_request(db, request_id)
    task = db.get(RequestTaskLive, task_id)
    require_record_for_agency(task, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=task.agency_id,
        child_travel_request_id=task.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    workflow = load_workflow(db, task.request_workflow_live_id)
    if workflow.status != WORKFLOW_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="Tasks can only be updated on active workflows.")

    if payload.is_completed is not None:
        _apply_task_status(task, TASK_STATUS_DONE if payload.is_completed else TASK_STATUS_OPEN, current_user)
        if payload.is_completed and task.completed_at:
            apply_task_completion_side_effects(workflow, task)

    if payload.status is not None:
        _apply_task_status(task, payload.status, current_user)
        if payload.status == TASK_STATUS_DONE and task.completed_at:
            apply_task_completion_side_effects(workflow, task)

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
    _maybe_auto_complete_workflow(workflow, current_user)

    touch_request(request, current_user)
    db.commit()
    return load_workflow(db, workflow.id)
