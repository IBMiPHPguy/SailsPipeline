from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.agency_custom_task_service import list_agency_custom_task_definitions
from app.services.workflow_task_catalog_service import build_system_task_catalog


def list_agency_task_inventory(db: Session, *, agency_id: str) -> list[dict]:
    placement_rows = (
        db.query(
            AgencyTaskTemplate.id.label("task_template_id"),
            AgencyTaskTemplate.task_key,
            AgencyTaskTemplate.task_title,
            AgencyTaskTemplate.description,
            AgencyTaskTemplate.sequence_order,
            AgencyWorkflowTemplate.id.label("workflow_template_id"),
            AgencyWorkflowTemplate.workflow_name,
        )
        .join(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
        )
        .all()
    )
    placement_by_key = {
        row.task_key: {
            "task_template_id": row.task_template_id,
            "task_title": row.task_title,
            "description": row.description or "",
            "workflow_template_id": row.workflow_template_id,
            "workflow_name": row.workflow_name,
            "sequence_order": row.sequence_order,
        }
        for row in placement_rows
        if row.task_key
    }

    inventory: list[dict] = []

    for catalog_item in build_system_task_catalog():
        placement = placement_by_key.get(catalog_item["task_key"])
        inventory.append(
            {
                "task_key": catalog_item["task_key"],
                "task_title": placement["task_title"] if placement else catalog_item["task_title"],
                "description": placement["description"] if placement else catalog_item["description"],
                "task_type": "builtin",
                "definition_id": None,
                "task_template_id": placement["task_template_id"] if placement else None,
                "workflow_template_id": placement["workflow_template_id"] if placement else None,
                "workflow_name": placement["workflow_name"] if placement else None,
                "sequence_order": placement["sequence_order"] if placement else None,
            }
        )

    for definition in list_agency_custom_task_definitions(db, agency_id=agency_id):
        placement = placement_by_key.get(definition.task_key)
        inventory.append(
            {
                "task_key": definition.task_key,
                "task_title": definition.task_title,
                "description": definition.description or "",
                "task_type": "library",
                "definition_id": definition.id,
                "task_template_id": placement["task_template_id"] if placement else None,
                "workflow_template_id": placement["workflow_template_id"] if placement else None,
                "workflow_name": placement["workflow_name"] if placement else None,
                "sequence_order": placement["sequence_order"] if placement else None,
            }
        )

    return sorted(inventory, key=lambda item: (item["task_type"], item["task_title"].lower()))
