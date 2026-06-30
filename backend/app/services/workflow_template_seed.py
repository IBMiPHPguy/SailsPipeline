"""Seed canonical workflow playbooks into agency_workflow_templates for every agency."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.constants import TASK_ACTION_CUSTOM_PANEL, WORKFLOW_TYPE_COMMUNICATE_RESEARCH, WORKFLOW_TYPE_RESEARCH
from app.models import Agency, AgencyTaskTemplate, AgencyWorkflowTemplate, RequestCommunication, RequestTask, RequestTaskLive, RequestWorkflow, RequestWorkflowLive
from app.workflow_helpers import (
    COMMUNICATE_RESEARCH_PREREQUISITE_KEYS,
    WORKFLOW_DEFINITIONS,
    WORKFLOW_SUCCESSORS,
    WORKFLOW_TASK_TEMPLATES,
)


def _new_id() -> str:
    return str(uuid.uuid4())


def replace_workflow_template_tasks_with_defaults(
    db: Session,
    workflow_template: AgencyWorkflowTemplate,
    workflow_type: str,
) -> None:
    task_templates = WORKFLOW_TASK_TEMPLATES.get(workflow_type, [])
    for template in task_templates:
        prerequisite_keys = COMMUNICATE_RESEARCH_PREREQUISITE_KEYS.get(template.task_key)
        db.add(
            AgencyTaskTemplate(
                id=_new_id(),
                workflow_template_id=workflow_template.id,
                task_title=template.title,
                sequence_order=template.sort_order,
                action_type=TASK_ACTION_CUSTOM_PANEL,
                task_key=template.task_key,
                description=template.description,
                prerequisite_task_keys=list(prerequisite_keys) if prerequisite_keys else None,
            )
        )


def wire_default_successor_link(
    db: Session,
    *,
    agency_id: str,
    workflow_template: AgencyWorkflowTemplate,
    workflow_type: str,
) -> None:
    successor_type = WORKFLOW_SUCCESSORS.get(workflow_type)
    if successor_type is None:
        workflow_template.successor_template_id = None
        return

    successor = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.workflow_type_key == successor_type,
            AgencyWorkflowTemplate.archived_at.is_(None),
        )
        .first()
    )
    workflow_template.successor_template_id = successor.id if successor else None


def seed_agency_workflow_templates(db: Session, agency_id: str) -> None:
    template_by_type: dict[str, tuple[AgencyWorkflowTemplate, bool]] = {}
    for workflow_type, definition in WORKFLOW_DEFINITIONS.items():
        row = (
            db.query(AgencyWorkflowTemplate)
            .filter(
                AgencyWorkflowTemplate.agency_id == agency_id,
                AgencyWorkflowTemplate.workflow_type_key == workflow_type,
            )
            .first()
        )
        if row is None:
            row = AgencyWorkflowTemplate(
                id=_new_id(),
                agency_id=agency_id,
                workflow_name=definition["name"],
                description=definition.get("description"),
                workflow_type_key=workflow_type,
            )
            db.add(row)
            db.flush()
            template_by_type[workflow_type] = (row, True)
        else:
            template_by_type[workflow_type] = (row, False)

    for workflow_type, successor_type in WORKFLOW_SUCCESSORS.items():
        parent_entry = template_by_type.get(workflow_type)
        successor_entry = template_by_type.get(successor_type)
        if parent_entry is None or successor_entry is None:
            continue
        parent, parent_is_new = parent_entry
        successor, _ = successor_entry
        if parent.archived_at is not None or successor.archived_at is not None:
            continue
        if parent_is_new and parent.successor_template_id is None:
            parent.successor_template_id = successor.id

    for workflow_type, task_templates in WORKFLOW_TASK_TEMPLATES.items():
        workflow_entry = template_by_type.get(workflow_type)
        if workflow_entry is None:
            continue
        workflow_template, workflow_is_new = workflow_entry
        if workflow_template.archived_at is not None:
            continue
        if not workflow_is_new:
            continue

        existing_tasks = (
            db.query(AgencyTaskTemplate)
            .filter(AgencyTaskTemplate.workflow_template_id == workflow_template.id)
            .count()
        )
        if existing_tasks > 0:
            continue

        replace_workflow_template_tasks_with_defaults(db, workflow_template, workflow_type)


def seed_all_agency_workflow_templates(db: Session) -> None:
    agencies = db.query(Agency).all()
    for agency in agencies:
        seed_agency_workflow_templates(db, agency.id)
    db.commit()


def migrate_legacy_workflows_to_live(db: Session) -> None:
    legacy_workflows = (
        db.query(RequestWorkflow)
        .filter(
            ~RequestWorkflow.id.in_(
                db.query(RequestWorkflowLive.legacy_workflow_id).filter(
                    RequestWorkflowLive.legacy_workflow_id.isnot(None)
                )
            )
        )
        .all()
    )
    if not legacy_workflows:
        return

    workflow_id_map: dict[int, str] = {}
    for legacy in legacy_workflows:
        live = RequestWorkflowLive(
            id=_new_id(),
            agency_id=legacy.agency_id,
            travel_request_id=legacy.travel_request_id,
            template_id=_resolve_template_id(db, legacy.agency_id, legacy.workflow_type),
            workflow_name=WORKFLOW_DEFINITIONS.get(legacy.workflow_type, {}).get("name", legacy.workflow_type),
            workflow_type_key=legacy.workflow_type,
            status=_map_legacy_workflow_status(legacy.status),
            parent_workflow_live_id=None,
            context=legacy.context,
            started_by_id=legacy.started_by_id,
            completed_by_id=legacy.completed_by_id,
            legacy_workflow_id=legacy.id,
            started_at=legacy.created_at,
            ended_at=legacy.completed_at,
        )
        db.add(live)
        db.flush()
        workflow_id_map[legacy.id] = live.id

    for legacy in legacy_workflows:
        if legacy.parent_workflow_id is not None:
            live_id = workflow_id_map.get(legacy.id)
            parent_live_id = workflow_id_map.get(legacy.parent_workflow_id)
            if live_id and parent_live_id:
                live_row = db.get(RequestWorkflowLive, live_id)
                if live_row is not None:
                    live_row.parent_workflow_live_id = parent_live_id

    legacy_tasks = db.query(RequestTask).all()
    task_id_map: dict[int, str] = {}
    for legacy_task in legacy_tasks:
        live_workflow_id = workflow_id_map.get(legacy_task.request_workflow_id)
        if live_workflow_id is None:
            continue
        if (
            db.query(RequestTaskLive)
            .filter(RequestTaskLive.legacy_task_id == legacy_task.id)
            .first()
        ):
            continue

        live_task = RequestTaskLive(
            id=_new_id(),
            agency_id=legacy_task.agency_id,
            request_workflow_live_id=live_workflow_id,
            travel_request_id=legacy_task.travel_request_id,
            template_task_id=None,
            task_key=legacy_task.task_key,
            task_title=legacy_task.title,
            description=legacy_task.description,
            sequence_order=legacy_task.sort_order,
            action_type=TASK_ACTION_CUSTOM_PANEL if legacy_task.task_key else "manual_check",
            is_completed=legacy_task.status == "Done",
            status=legacy_task.status,
            due_at=legacy_task.due_at,
            result=legacy_task.result,
            completed_by_id=legacy_task.completed_by_id,
            completed_at=legacy_task.completed_at,
            legacy_task_id=legacy_task.id,
        )
        db.add(live_task)
        task_id_map[legacy_task.id] = live_task.id

    for communication in db.query(RequestCommunication).filter(
        RequestCommunication.request_workflow_id.isnot(None),
        RequestCommunication.request_workflow_live_id.is_(None),
    ):
        live_id = workflow_id_map.get(communication.request_workflow_id)
        if live_id is not None:
            communication.request_workflow_live_id = live_id

    db.commit()


def _resolve_template_id(db: Session, agency_id: str, workflow_type: str) -> str | None:
    template = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.workflow_type_key == workflow_type,
        )
        .first()
    )
    return template.id if template else None


def _map_legacy_workflow_status(status: str) -> str:
    if status == "Cancelled":
        return "Terminated"
    return status
