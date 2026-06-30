import pytest

from datetime import timedelta

from app.constants import TASK_STATUS_DONE, TASK_STATUS_OPEN, WORKFLOW_STATUS_ACTIVE
from app.models import AgencyTaskTemplate, AgencyWorkflowTemplate, RequestTaskLive, RequestWorkflowLive, TravelRequest, User
from app.schemas import RequestTaskUpdate
from app.security import hash_password
from app.services.workflow_service import update_task
from app.services.workflow_template_service import create_agency_workflow_template
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import set_current_agency_id
from app.workflow_helpers import TASK_KEY_FOLLOW_UP_RESEARCH, TASK_KEY_SEND_RESEARCH_COMMUNICATION


def _user(db) -> User:
    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="phase7-admin",
        email="phase7-admin@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    db.add(user)
    db.flush()
    return user


def _open_request(db, user: User) -> TravelRequest:
    from datetime import date

    from app.constants import REQUEST_STATUS_OPEN

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Pat",
        last_name="Cruiser",
        email="pat@example.com",
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
    )
    db.add(request)
    db.flush()
    return request


@pytest.mark.integration
def test_catalog_includes_task_behavior_metadata(client, auth_headers):
    response = client.get("/api/agency-task-catalog", headers=auth_headers)
    assert response.status_code == 200
    send_task = next(item for item in response.json() if item["task_key"] == TASK_KEY_SEND_RESEARCH_COMMUNICATION)
    assert send_task["on_complete_schedule_follow_up_task_key"] == TASK_KEY_FOLLOW_UP_RESEARCH
    assert send_task["follow_up_due_days"] == 3

    follow_up = next(item for item in response.json() if item["task_key"] == TASK_KEY_FOLLOW_UP_RESEARCH)
    assert follow_up["allows_reached_out"] is True


def test_update_task_schedules_follow_up_from_metadata_on_custom_workflow(db):
    set_current_agency_id(DEFAULT_AGENCY_ID)
    user = _user(db)
    request = _open_request(db, user)

    custom_template = create_agency_workflow_template(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        workflow_name="Custom communicate",
    )
    send_task_template = AgencyTaskTemplate(
        id="send-template-id",
        workflow_template_id=custom_template.id,
        task_title="Send research communication",
        sequence_order=1,
        action_type="custom_panel",
        task_key=TASK_KEY_SEND_RESEARCH_COMMUNICATION,
    )
    follow_up_template = AgencyTaskTemplate(
        id="followup-template-id",
        workflow_template_id=custom_template.id,
        task_title="Follow up on research communication",
        sequence_order=2,
        action_type="custom_panel",
        task_key=TASK_KEY_FOLLOW_UP_RESEARCH,
    )
    db.add_all([send_task_template, follow_up_template])

    workflow = RequestWorkflowLive(
        id="workflow-custom-communicate",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        template_id=custom_template.id,
        workflow_name=custom_template.workflow_name,
        workflow_type_key=None,
        status=WORKFLOW_STATUS_ACTIVE,
        started_by_id=user.id,
    )
    db.add(workflow)
    db.flush()

    send_live = RequestTaskLive(
        id="send-live-id",
        agency_id=DEFAULT_AGENCY_ID,
        request_workflow_live_id=workflow.id,
        travel_request_id=request.id,
        template_task_id=send_task_template.id,
        task_key=TASK_KEY_SEND_RESEARCH_COMMUNICATION,
        task_title=send_task_template.task_title,
        sequence_order=1,
        action_type="custom_panel",
        status=TASK_STATUS_OPEN,
        is_completed=False,
    )
    follow_up_live = RequestTaskLive(
        id="followup-live-id",
        agency_id=DEFAULT_AGENCY_ID,
        request_workflow_live_id=workflow.id,
        travel_request_id=request.id,
        template_task_id=follow_up_template.id,
        task_key=TASK_KEY_FOLLOW_UP_RESEARCH,
        task_title=follow_up_template.task_title,
        sequence_order=2,
        action_type="custom_panel",
        status=TASK_STATUS_OPEN,
        is_completed=False,
    )
    db.add_all([send_live, follow_up_live])
    db.commit()

    update_task(
        db,
        request_id=request.id,
        task_id=send_live.id,
        payload=RequestTaskUpdate(status=TASK_STATUS_DONE),
        current_user=user,
    )

    db.refresh(follow_up_live)
    db.refresh(send_live)
    assert follow_up_live.due_at is not None
    assert send_live.completed_at is not None
    assert follow_up_live.due_at - send_live.completed_at == timedelta(days=3)
