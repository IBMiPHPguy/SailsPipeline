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


def test_dedupe_reassigns_live_tasks_before_deleting_duplicate_template(db):
    from datetime import UTC, date, datetime

    from app.constants import REQUEST_STATUS_OPEN, WORKFLOW_STATUS_ACTIVE
    from app.models import RequestTaskLive, RequestWorkflowLive, TravelRequest, User
    from app.security import hash_password
    from app.services.workflow_template_seed import dedupe_workflow_template_task_keys
    from app.tenant_constants import DEFAULT_AGENCY_ID

    research = _research_template(db)
    canonical_task = next(task for task in research.task_templates if task.task_key == "research_cruise_options")
    duplicate_task = AgencyTaskTemplate(
        id=str(uuid.uuid4()),
        workflow_template_id=research.id,
        task_title=canonical_task.task_title,
        sequence_order=canonical_task.sequence_order + 10,
        action_type=canonical_task.action_type,
        task_key=canonical_task.task_key,
        description=canonical_task.description,
    )
    db.add(duplicate_task)

    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="dedupe-live-task-user",
        email="dedupe-live-task@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    db.add(user)
    db.flush()

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        close_reason=None,
        created_by=user,
        updated_by=user,
        updated_at=datetime.now(UTC),
    )
    db.add(request)
    db.flush()

    workflow = RequestWorkflowLive(
        id=str(uuid.uuid4()),
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        template_id=research.id,
        workflow_name=research.workflow_name,
        workflow_type_key=research.workflow_type_key,
        status=WORKFLOW_STATUS_ACTIVE,
        started_by_id=user.id,
    )
    db.add(workflow)
    db.flush()

    live_task = RequestTaskLive(
        id=str(uuid.uuid4()),
        agency_id=DEFAULT_AGENCY_ID,
        request_workflow_live_id=workflow.id,
        travel_request_id=request.id,
        template_task_id=duplicate_task.id,
        task_key=duplicate_task.task_key,
        task_title=duplicate_task.task_title,
        sequence_order=duplicate_task.sequence_order,
        action_type=duplicate_task.action_type,
    )
    db.add(live_task)
    db.commit()

    removed = dedupe_workflow_template_task_keys(db, research)
    db.commit()

    assert removed == 1
    db.refresh(live_task)
    assert live_task.template_task_id == canonical_task.id
    assert db.get(AgencyTaskTemplate, duplicate_task.id) is None


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