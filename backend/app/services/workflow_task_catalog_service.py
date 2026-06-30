from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants import TASK_ACTION_CUSTOM_PANEL
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.workflow_helpers import COMMUNICATE_RESEARCH_PREREQUISITE_KEYS, WORKFLOW_TASK_TEMPLATES


def build_system_task_catalog() -> list[dict]:
    """One entry per built-in task_key from WORKFLOW_TASK_TEMPLATES."""
    catalog_by_key: dict[str, dict] = {}
    for _workflow_type, task_templates in WORKFLOW_TASK_TEMPLATES.items():
        for template in task_templates:
            if template.task_key in catalog_by_key:
                continue
            prerequisite_keys = COMMUNICATE_RESEARCH_PREREQUISITE_KEYS.get(template.task_key)
            catalog_by_key[template.task_key] = {
                "task_key": template.task_key,
                "task_title": template.title,
                "description": template.description,
                "action_type": TASK_ACTION_CUSTOM_PANEL,
                "prerequisite_task_keys": list(prerequisite_keys) if prerequisite_keys else [],
            }
    return [catalog_by_key[key] for key in sorted(catalog_by_key)]


def list_placed_task_keys(db: Session, *, agency_id: str) -> list[str]:
    rows = (
        db.query(AgencyTaskTemplate.task_key)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyTaskTemplate.task_key.isnot(None),
        )
        .all()
    )
    return sorted({row[0] for row in rows if row[0]})


def get_agency_task_availability(db: Session, *, agency_id: str) -> dict:
    catalog = build_system_task_catalog()
    placed_keys = set(list_placed_task_keys(db, agency_id=agency_id))
    available_tasks = [item for item in catalog if item["task_key"] not in placed_keys]
    return {
        "available_tasks": available_tasks,
        "placed_task_keys": sorted(placed_keys),
        "available_count": len(available_tasks),
    }


def assert_task_key_available_for_agency(
    db: Session,
    *,
    agency_id: str,
    task_key: str,
    exclude_task_id: str | None = None,
) -> None:
    if not task_key:
        return

    query = (
        db.query(AgencyTaskTemplate)
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyTaskTemplate.task_key == task_key,
        )
    )
    if exclude_task_id is not None:
        query = query.filter(AgencyTaskTemplate.id != exclude_task_id)

    if query.first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Built-in task '{task_key}' is already on a playbook for this agency.",
        )


def get_catalog_item(task_key: str) -> dict | None:
    for item in build_system_task_catalog():
        if item["task_key"] == task_key:
            return item
    return None
