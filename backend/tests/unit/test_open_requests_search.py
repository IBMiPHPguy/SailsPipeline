from datetime import UTC, date, datetime, timedelta
import uuid

from app.constants import REQUEST_STATUS_OPEN, TASK_STATUS_OPEN, WORKFLOW_STATUS_ACTIVE, WORKFLOW_TYPE_RESEARCH
from app.models import RequestTaskLive, RequestWorkflowLive, TravelRequest, User
from app.security import hash_password
from app.services.request_service import search_open_requests
from app.tenant_constants import DEFAULT_AGENCY_ID


def _create_user(db, *, username: str, email: str) -> User:
    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username=username,
        email=email,
        password_hash=hash_password("ValidPass1!"),
    )
    db.add(user)
    db.flush()
    return user


def _create_open_request(
    db,
    *,
    user: User,
    first_name: str,
    last_name: str,
    email: str,
    destination: str,
    task_title: str = "Research cruise options",
) -> TravelRequest:
    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination=destination,
        destination_details={"caribbean_regions": ["Eastern"]} if destination == "Caribbean" else None,
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
        workflow_name="Research",
        workflow_type_key=WORKFLOW_TYPE_RESEARCH,
        status=WORKFLOW_STATUS_ACTIVE,
        started_by_id=user.id,
        started_at=datetime.now(UTC),
    )
    db.add(workflow)
    db.flush()

    task = RequestTaskLive(
        id=str(uuid.uuid4()),
        agency_id=DEFAULT_AGENCY_ID,
        request_workflow_live_id=workflow.id,
        travel_request_id=request.id,
        task_key="research_cruise_options",
        task_title=task_title,
        status=TASK_STATUS_OPEN,
        sequence_order=1,
        is_completed=False,
    )
    db.add(task)
    db.flush()
    return request


def test_search_open_requests_filters_by_client_name(db):
    agent = _create_user(db, username="agent-open-1", email="agent-open-1@example.com")
    _create_open_request(
        db,
        user=agent,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        destination="Caribbean",
    )
    _create_open_request(
        db,
        user=agent,
        first_name="John",
        last_name="Sailor",
        email="john@example.com",
        destination="Caribbean",
    )
    db.commit()

    items, total = search_open_requests(db, query="Jane")

    assert total == 1
    assert len(items) == 1
    assert items[0].first_name == "Jane"


def test_search_open_requests_matches_task_title(db):
    agent = _create_user(db, username="agent-open-2", email="agent-open-2@example.com")
    _create_open_request(
        db,
        user=agent,
        first_name="Amy",
        last_name="Wave",
        email="amy@example.com",
        destination="Caribbean",
        task_title="Upload research document",
    )
    _create_open_request(
        db,
        user=agent,
        first_name="Bob",
        last_name="Wave",
        email="bob@example.com",
        destination="Caribbean",
        task_title="Research cruise options",
    )
    db.commit()

    items, total = search_open_requests(db, query="Upload research")

    assert total == 1
    assert items[0].first_name == "Amy"
    assert items[0].next_open_task is not None
    assert items[0].next_open_task.title == "Upload research document"


def test_search_open_requests_paginates_results(db):
    agent = _create_user(db, username="agent-open-3", email="agent-open-3@example.com")
    base_time = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    for index in range(3):
        request = _create_open_request(
            db,
            user=agent,
            first_name=f"Client{index}",
            last_name="Open",
            email=f"client{index}@example.com",
            destination="Caribbean",
        )
        request.updated_at = base_time - timedelta(days=index)
    db.commit()

    page_one, total = search_open_requests(db, page=1, page_size=2)
    page_two, _ = search_open_requests(db, page=2, page_size=2)

    assert total == 3
    assert len(page_one) == 2
    assert len(page_two) == 1
