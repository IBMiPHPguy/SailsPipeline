import pytest
from fastapi import HTTPException

from app.constants import WORKFLOW_TYPE_RESEARCH
from app.models import AgencyWorkflowTemplate
from app.services.workflow_template_seed import seed_agency_workflow_templates
from app.services.workflow_template_service import (
    create_agency_workflow_template,
    delete_agency_task_template,
    reset_agency_workflow_template_to_default,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import set_current_agency_id
from app.workflow_helpers import WORKFLOW_DEFINITIONS, WORKFLOW_TASK_TEMPLATES


def _research_template(db) -> AgencyWorkflowTemplate:
    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.flush()
    return (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
        )
        .one()
    )


def test_reset_recommended_workflow_restores_defaults(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    template = _research_template(db)
    template.workflow_name = "Custom research name"
    template.description = "Custom description"
    db.commit()

    first_task = template.task_templates[0]
    delete_agency_task_template(db, task_id=first_task.id)

    template, message = reset_agency_workflow_template_to_default(db, template_id=template.id)
    definition = WORKFLOW_DEFINITIONS[WORKFLOW_TYPE_RESEARCH]

    assert template.workflow_name == definition["name"]
    assert template.description == definition["description"]
    assert len(template.task_templates) == len(WORKFLOW_TASK_TEMPLATES[WORKFLOW_TYPE_RESEARCH])
    assert {task.task_key for task in template.task_templates} == {
        row.task_key for row in WORKFLOW_TASK_TEMPLATES[WORKFLOW_TYPE_RESEARCH]
    }
    assert "restored" in message.lower()


def test_reset_rejects_custom_workflow(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    custom = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Custom only",
    )

    with pytest.raises(HTTPException) as exc_info:
        reset_agency_workflow_template_to_default(db, template_id=custom.id)

    assert exc_info.value.status_code == 400
    assert "recommended" in exc_info.value.detail.lower()
