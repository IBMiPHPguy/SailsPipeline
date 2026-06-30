import pytest
from fastapi import HTTPException

from app.constants import WORKFLOW_TYPE_RESEARCH
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.workflow_template_seed import seed_agency_workflow_templates
from app.services.workflow_template_service import update_agency_task_template
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import set_current_agency_id


def _research_tasks(db) -> list[AgencyTaskTemplate]:
    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.flush()
    template = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
        )
        .one()
    )
    return sorted(template.task_templates, key=lambda row: row.sequence_order)


def test_update_task_sequence_order_moves_task(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    tasks = _research_tasks(db)
    last_task = tasks[-1]

    update_agency_task_template(db, task_id=last_task.id, sequence_order=1)

    refreshed = _research_tasks(db)
    assert refreshed[0].id == last_task.id
    assert [task.sequence_order for task in refreshed] == list(range(1, len(refreshed) + 1))


def test_update_task_sequence_order_rejects_out_of_range(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    tasks = _research_tasks(db)

    with pytest.raises(HTTPException) as exc_info:
        update_agency_task_template(db, task_id=tasks[0].id, sequence_order=len(tasks) + 5)

    assert exc_info.value.status_code == 400
