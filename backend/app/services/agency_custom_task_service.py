from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants import TASK_ACTION_MANUAL_CHECK
from app.models import AgencyCustomTaskDefinition, AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.agency_service import require_record_for_agency
from app.services.workflow_task_catalog_service import assert_task_key_available_for_agency
from app.tenant_context import require_current_agency_id


def _new_id() -> str:
    return str(uuid.uuid4())


def _custom_task_key(definition_id: str) -> str:
    return f"custom_{definition_id.replace('-', '')}"


def list_agency_custom_task_definitions(db: Session, *, agency_id: str) -> list[AgencyCustomTaskDefinition]:
    return (
        db.query(AgencyCustomTaskDefinition)
        .filter(AgencyCustomTaskDefinition.agency_id == agency_id)
        .order_by(AgencyCustomTaskDefinition.task_title.asc())
        .all()
    )


def load_agency_custom_task_definition(db: Session, *, definition_id: str) -> AgencyCustomTaskDefinition:
    definition = db.get(AgencyCustomTaskDefinition, definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="Custom task definition not found.")
    require_record_for_agency(definition, agency_id=require_current_agency_id())
    return definition


def create_agency_custom_task_definition(
    db: Session,
    *,
    agency_id: str,
    task_title: str,
    description: str | None = None,
) -> AgencyCustomTaskDefinition:
    title = task_title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required.")

    definition_id = _new_id()
    definition = AgencyCustomTaskDefinition(
        id=definition_id,
        agency_id=agency_id,
        task_key=_custom_task_key(definition_id),
        task_title=title,
        description=description.strip() if description else None,
        action_type=TASK_ACTION_MANUAL_CHECK,
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition


def update_agency_custom_task_definition(
    db: Session,
    *,
    definition_id: str,
    task_title: str | None = None,
    description: str | None = None,
) -> AgencyCustomTaskDefinition:
    definition = load_agency_custom_task_definition(db, definition_id=definition_id)

    if task_title is not None:
        title = task_title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Task title is required.")
        definition.task_title = title

    if description is not None:
        definition.description = description.strip() or None

    placed_task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == definition.agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
            AgencyTaskTemplate.task_key == definition.task_key,
        )
        .one_or_none()
    )
    if placed_task is not None:
        if task_title is not None:
            placed_task.task_title = definition.task_title
        if description is not None:
            placed_task.description = definition.description

    db.commit()
    db.refresh(definition)
    return definition


def delete_agency_custom_task_definition(db: Session, *, definition_id: str) -> None:
    from app.services.workflow_template_service import renumber_workflow_task_templates

    definition = load_agency_custom_task_definition(db, definition_id=definition_id)
    placed_task = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == definition.agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
            AgencyTaskTemplate.task_key == definition.task_key,
        )
        .one_or_none()
    )
    if placed_task is not None:
        template_id = placed_task.workflow_template_id
        db.delete(placed_task)
        db.flush()
        renumber_workflow_task_templates(db, template_id)

    db.delete(definition)
    db.commit()


def custom_definition_to_catalog_item(definition: AgencyCustomTaskDefinition) -> dict:
    return {
        "task_key": definition.task_key,
        "task_title": definition.task_title,
        "description": definition.description or "",
        "action_type": definition.action_type,
        "prerequisite_task_keys": [],
    }


def get_custom_definition_by_task_key(
    db: Session,
    *,
    agency_id: str,
    task_key: str,
) -> AgencyCustomTaskDefinition | None:
    return (
        db.query(AgencyCustomTaskDefinition)
        .filter(
            AgencyCustomTaskDefinition.agency_id == agency_id,
            AgencyCustomTaskDefinition.task_key == task_key,
        )
        .one_or_none()
    )


def create_agency_task_from_custom_definition(
    db: Session,
    *,
    template_id: str,
    task_key: str,
    sequence_order: int | None = None,
) -> AgencyTaskTemplate:
    from app.services.workflow_template_service import load_workflow_template, renumber_workflow_task_templates

    workflow_template = load_workflow_template(db, template_id)
    definition = get_custom_definition_by_task_key(
        db,
        agency_id=workflow_template.agency_id,
        task_key=task_key,
    )
    if definition is None:
        raise HTTPException(status_code=400, detail="Unknown custom checklist task.")

    assert_task_key_available_for_agency(
        db,
        agency_id=workflow_template.agency_id,
        task_key=task_key,
    )

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
        task_title=definition.task_title,
        sequence_order=resolved_order,
        action_type=definition.action_type,
        task_key=definition.task_key,
        description=definition.description,
    )
    db.add(task)
    db.flush()
    renumber_workflow_task_templates(db, workflow_template.id)
    db.commit()
    db.refresh(task)
    return task
