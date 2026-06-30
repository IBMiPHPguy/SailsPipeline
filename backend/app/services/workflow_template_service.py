from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.constants import TASK_ACTION_MANUAL_CHECK
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate, RequestTaskLive, User
from app.services.agency_service import require_record_for_agency
from app.services.workflow_task_catalog_service import (
    assert_task_key_available_for_agency,
    get_catalog_item,
)
from app.services.workflow_service import terminate_active_live_workflows_for_template
from app.services.workflow_template_seed import (
    replace_workflow_template_tasks_with_defaults,
    wire_default_successor_link,
)
from app.tenant_context import require_current_agency_id
from app.workflow_helpers import WORKFLOW_DEFINITIONS


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _active_workflow_templates_query(db: Session):
    return db.query(AgencyWorkflowTemplate).filter(AgencyWorkflowTemplate.archived_at.is_(None))


def load_workflow_template(
    db: Session,
    template_id: str,
    *,
    require_active: bool = True,
) -> AgencyWorkflowTemplate:
    template = (
        db.query(AgencyWorkflowTemplate)
        .options(joinedload(AgencyWorkflowTemplate.task_templates))
        .filter(AgencyWorkflowTemplate.id == template_id)
        .one()
    )
    require_record_for_agency(template, agency_id=require_current_agency_id())
    if require_active and template.archived_at is not None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return template


def list_agency_workflow_templates(db: Session, *, agency_id: str) -> list[AgencyWorkflowTemplate]:
    return (
        _active_workflow_templates_query(db)
        .options(joinedload(AgencyWorkflowTemplate.task_templates))
        .filter(AgencyWorkflowTemplate.agency_id == agency_id)
        .order_by(AgencyWorkflowTemplate.workflow_name.asc())
        .all()
    )


def create_agency_workflow_template(
    db: Session,
    *,
    agency_id: str,
    workflow_name: str,
    description: str | None = None,
) -> AgencyWorkflowTemplate:
    name = workflow_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Workflow name is required.")

    template = AgencyWorkflowTemplate(
        id=_new_id(),
        agency_id=agency_id,
        workflow_name=name,
        description=description.strip() if description else None,
    )
    db.add(template)
    db.commit()
    return load_workflow_template(db, template.id)


def update_agency_workflow_template(
    db: Session,
    *,
    template_id: str,
    workflow_name: str | None = None,
    description: str | None = None,
) -> AgencyWorkflowTemplate:
    template = load_workflow_template(db, template_id)
    if workflow_name is not None:
        name = workflow_name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Workflow name is required.")
        template.workflow_name = name
    if description is not None:
        template.description = description.strip() or None
    db.commit()
    return load_workflow_template(db, template.id)


def archive_agency_workflow_template(db: Session, *, template_id: str, current_user: User) -> None:
    template = load_workflow_template(db, template_id, require_active=False)
    if template.archived_at is not None:
        raise HTTPException(status_code=400, detail="Workflow is already removed.")

    terminate_active_live_workflows_for_template(
        db,
        template_id=template.id,
        agency_id=template.agency_id,
        current_user=current_user,
    )

    db.query(AgencyWorkflowTemplate).filter(
        AgencyWorkflowTemplate.successor_template_id == template.id,
    ).update({AgencyWorkflowTemplate.successor_template_id: None}, synchronize_session=False)

    template.successor_template_id = None
    template.archived_at = _utcnow_naive()

    task_ids = [task.id for task in template.task_templates]
    if task_ids:
        db.query(RequestTaskLive).filter(RequestTaskLive.template_task_id.in_(task_ids)).update(
            {RequestTaskLive.template_task_id: None},
            synchronize_session=False,
        )

    for task in list(template.task_templates):
        db.delete(task)

    db.commit()


def delete_agency_workflow_template(db: Session, *, template_id: str, current_user: User) -> None:
    archive_agency_workflow_template(db, template_id=template_id, current_user=current_user)


RESET_TO_DEFAULT_MESSAGE = (
    "Workflow restored to the product default title, description, successor link, and task sequence. "
    "Prior template task customizations were replaced."
)


def reset_agency_workflow_template_to_default(
    db: Session,
    *,
    template_id: str,
) -> tuple[AgencyWorkflowTemplate, str]:
    template = load_workflow_template(db, template_id)
    workflow_type = template.workflow_type_key
    if not workflow_type:
        raise HTTPException(status_code=400, detail="Only recommended workflows can be reset to default.")

    definition = WORKFLOW_DEFINITIONS.get(workflow_type)
    if definition is None:
        raise HTTPException(status_code=400, detail="Unknown recommended workflow type.")

    template.workflow_name = definition["name"]
    template.description = definition.get("description")

    task_ids = [task.id for task in template.task_templates]
    if task_ids:
        db.query(RequestTaskLive).filter(RequestTaskLive.template_task_id.in_(task_ids)).update(
            {RequestTaskLive.template_task_id: None},
            synchronize_session=False,
        )

    for task in list(template.task_templates):
        db.delete(task)
    db.flush()

    replace_workflow_template_tasks_with_defaults(db, template, workflow_type)
    wire_default_successor_link(
        db,
        agency_id=template.agency_id,
        workflow_template=template,
        workflow_type=workflow_type,
    )
    db.commit()
    return load_workflow_template(db, template.id), RESET_TO_DEFAULT_MESSAGE


def create_agency_task_from_catalog(
    db: Session,
    *,
    template_id: str,
    task_key: str,
    task_title: str | None = None,
    sequence_order: int | None = None,
) -> AgencyTaskTemplate:
    workflow_template = load_workflow_template(db, template_id)
    catalog_item = get_catalog_item(task_key)
    if catalog_item is None:
        raise HTTPException(status_code=400, detail="Unknown built-in task.")

    assert_task_key_available_for_agency(
        db,
        agency_id=workflow_template.agency_id,
        task_key=task_key,
    )

    resolved_title = task_title.strip() if task_title else catalog_item["task_title"]
    if not resolved_title:
        raise HTTPException(status_code=400, detail="Task title is required.")

    target_tasks = sorted(workflow_template.task_templates, key=lambda row: row.sequence_order)
    if sequence_order is None or sequence_order > len(target_tasks) + 1:
        resolved_order = max((row.sequence_order for row in target_tasks), default=0) + 1
    else:
        resolved_order = sequence_order
        for row in target_tasks:
            if row.sequence_order >= sequence_order:
                row.sequence_order += 1

    task = AgencyTaskTemplate(
        id=_new_id(),
        workflow_template_id=workflow_template.id,
        task_title=resolved_title,
        sequence_order=resolved_order,
        action_type=catalog_item["action_type"],
        task_key=catalog_item["task_key"],
        description=catalog_item["description"],
        prerequisite_task_keys=catalog_item["prerequisite_task_keys"] or None,
    )
    db.add(task)
    db.flush()
    renumber_workflow_task_templates(db, workflow_template.id)
    db.commit()
    db.refresh(task)
    return task


def create_agency_task_template(
    db: Session,
    *,
    template_id: str,
    task_title: str,
) -> AgencyTaskTemplate:
    workflow_template = load_workflow_template(db, template_id)
    title = task_title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required.")

    max_order = max((task.sequence_order for task in workflow_template.task_templates), default=0)
    task = AgencyTaskTemplate(
        id=_new_id(),
        workflow_template_id=workflow_template.id,
        task_title=title,
        sequence_order=max_order + 1,
        action_type=TASK_ACTION_MANUAL_CHECK,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_agency_task_template(
    db: Session,
    *,
    task_id: str,
    task_title: str | None = None,
    description: str | None = None,
    sequence_order: int | None = None,
) -> AgencyTaskTemplate:
    task = db.get(AgencyTaskTemplate, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task template not found.")
    template = load_workflow_template(db, task.workflow_template_id)

    if task_title is not None:
        title = task_title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Task title is required.")
        task.task_title = title

    if description is not None:
        task.description = description.strip() or None

    if sequence_order is not None:
        _set_task_sequence_order(db, template=template, task=task, sequence_order=sequence_order)

    db.commit()
    db.refresh(task)
    return task


def _set_task_sequence_order(
    db: Session,
    *,
    template: AgencyWorkflowTemplate,
    task: AgencyTaskTemplate,
    sequence_order: int,
) -> None:
    ordered = sorted(template.task_templates, key=lambda row: row.sequence_order)
    current_index = next((idx for idx, row in enumerate(ordered) if row.id == task.id), None)
    if current_index is None:
        raise HTTPException(status_code=404, detail="Task template not found.")

    if sequence_order < 1 or sequence_order > len(ordered):
        raise HTTPException(status_code=400, detail="Sequence order is out of range.")

    if current_index == sequence_order - 1:
        return

    ordered.pop(current_index)
    ordered.insert(sequence_order - 1, task)
    for index, row in enumerate(ordered, start=1):
        row.sequence_order = index


def delete_agency_task_template(db: Session, *, task_id: str) -> AgencyWorkflowTemplate:
    task = db.get(AgencyTaskTemplate, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task template not found.")
    template_id = task.workflow_template_id
    load_workflow_template(db, template_id)
    db.delete(task)
    db.flush()
    _renumber_task_templates(db, template_id)
    db.commit()
    return load_workflow_template(db, template_id)


def move_agency_task_template(
    db: Session,
    *,
    task_id: str,
    direction: str,
) -> AgencyWorkflowTemplate:
    task = db.get(AgencyTaskTemplate, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task template not found.")
    template = load_workflow_template(db, task.workflow_template_id)
    ordered = sorted(template.task_templates, key=lambda row: row.sequence_order)
    index = next((idx for idx, row in enumerate(ordered) if row.id == task.id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Task template not found.")

    if direction == "up" and index > 0:
        swap = ordered[index - 1]
        task.sequence_order, swap.sequence_order = swap.sequence_order, task.sequence_order
    elif direction == "down" and index < len(ordered) - 1:
        swap = ordered[index + 1]
        task.sequence_order, swap.sequence_order = swap.sequence_order, task.sequence_order
    else:
        raise HTTPException(status_code=400, detail="Task cannot move further in that direction.")

    db.commit()
    return load_workflow_template(db, template.id)


def transfer_agency_task_to_workflow(
    db: Session,
    *,
    task_id: str,
    target_workflow_template_id: str,
    sequence_order: int | None = None,
) -> tuple[AgencyWorkflowTemplate, AgencyWorkflowTemplate]:
    task = db.get(AgencyTaskTemplate, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task template not found.")

    source_template_id = task.workflow_template_id
    if source_template_id == target_workflow_template_id:
        raise HTTPException(status_code=400, detail="Task is already on that workflow.")

    source_template = load_workflow_template(db, source_template_id)
    target_template = load_workflow_template(db, target_workflow_template_id)
    if source_template.agency_id != target_template.agency_id:
        raise HTTPException(status_code=400, detail="Target workflow not found.")

    if task.task_key:
        assert_task_key_available_for_agency(
            db,
            agency_id=source_template.agency_id,
            task_key=task.task_key,
            exclude_task_id=task.id,
        )

    target_tasks = sorted(target_template.task_templates, key=lambda row: row.sequence_order)
    if sequence_order is None or sequence_order > len(target_tasks) + 1:
        task.sequence_order = max((row.sequence_order for row in target_tasks), default=0) + 1
    else:
        task.sequence_order = sequence_order
        for row in target_tasks:
            if row.sequence_order >= sequence_order:
                row.sequence_order += 1

    task.workflow_template_id = target_workflow_template_id
    db.flush()
    _renumber_task_templates(db, source_template_id)
    _renumber_task_templates(db, target_workflow_template_id)
    db.commit()
    return (
        load_workflow_template(db, source_template_id),
        load_workflow_template(db, target_workflow_template_id),
    )


def _renumber_task_templates(db: Session, template_id: str) -> None:
    tasks = (
        db.query(AgencyTaskTemplate)
        .filter(AgencyTaskTemplate.workflow_template_id == template_id)
        .order_by(AgencyTaskTemplate.sequence_order.asc(), AgencyTaskTemplate.id.asc())
        .all()
    )
    for index, task in enumerate(tasks, start=1):
        task.sequence_order = index


def renumber_workflow_task_templates(db: Session, template_id: str) -> None:
    _renumber_task_templates(db, template_id)
