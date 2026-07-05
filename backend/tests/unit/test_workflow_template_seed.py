import uuid

from app.constants import WORKFLOW_TYPE_COMMUNICATE_RESEARCH, WORKFLOW_TYPE_RESEARCH
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate
from app.services.workflow_template_seed import (
    _workflow_template_task_count,
    replace_workflow_template_tasks_with_defaults,
    seed_agency_workflow_templates,
)
from app.tenant_constants import DEFAULT_AGENCY_ID

def _research_template(db) -> AgencyWorkflowTemplate:
    return (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_RESEARCH,
        )
        .one()
    )


def _communicate_template(db) -> AgencyWorkflowTemplate:
    return (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == DEFAULT_AGENCY_ID,
            AgencyWorkflowTemplate.workflow_type_key == WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
        )
        .one()
    )


def test_seed_does_not_re_add_deleted_task(db):
    communicate = _communicate_template(db)
    task = (
        db.query(AgencyTaskTemplate)
        .filter(
            AgencyTaskTemplate.workflow_template_id == communicate.id,
            AgencyTaskTemplate.task_key == "client_response",
        )
        .one()
    )
    task_id = task.id
    db.delete(task)
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.commit()

    assert db.get(AgencyTaskTemplate, task_id) is None
    assert (
        db.query(AgencyTaskTemplate)
        .filter(
            AgencyTaskTemplate.workflow_template_id == communicate.id,
            AgencyTaskTemplate.task_key == "client_response",
        )
        .first()
        is None
    )


def test_seed_does_not_reset_cleared_successor(db):
    research = _research_template(db)
    research.successor_template_id = None
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.commit()
    db.refresh(research)

    assert research.successor_template_id is None


def test_seed_sets_successor_on_first_onboard(db):
    communicate = _communicate_template(db)
    research = _research_template(db)
    for task in list(research.task_templates):
        db.delete(task)
    db.delete(research)
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.commit()

    research = _research_template(db)
    assert research.successor_template_id == communicate.id


def test_seed_creates_missing_workflow_type(db):
    research = _research_template(db)
    for task in list(research.task_templates):
        db.delete(task)
    db.delete(research)
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.commit()

    recreated = _research_template(db)
    assert recreated.workflow_name == "Research"
    assert recreated.task_templates


def test_seed_dedupes_duplicate_recommended_tasks(db):
    research = _research_template(db)
    for task in list(research.task_templates):
        db.add(
            AgencyTaskTemplate(
                id=str(uuid.uuid4()),
                workflow_template_id=research.id,
                task_title=task.task_title,
                sequence_order=task.sequence_order + 10,
                action_type=task.action_type,
                task_key=task.task_key,
                description=task.description,
            )
        )
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    db.commit()
    db.refresh(research)

    task_keys = [task.task_key for task in research.task_templates]
    assert len(task_keys) == len(set(task_keys))
    assert len(task_keys) == 4


def test_repair_seed_and_backfill_do_not_double_tasks(db):
    research = _research_template(db)
    for task in list(research.task_templates):
        db.delete(task)
    db.delete(research)
    db.commit()

    seed_agency_workflow_templates(db, DEFAULT_AGENCY_ID)
    research = _research_template(db)
    if _workflow_template_task_count(db, research) == 0:
        replace_workflow_template_tasks_with_defaults(db, research, WORKFLOW_TYPE_RESEARCH)
    db.commit()

    research = _research_template(db)
    assert len(research.task_templates) == 4