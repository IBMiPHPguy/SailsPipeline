from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.constants import STALE_DAYS, TASK_STATUS_OPEN, WORKFLOW_STATUS_ACTIVE, WORKFLOW_TYPE_RESEARCH
from app.services.request_service import (
    build_dashboard_open_request,
    is_stale_by_last_worked,
    resolve_last_worked,
    resolve_next_open_task,
)


def test_is_stale_by_last_worked_handles_aware_and_naive_datetimes():
    stale_aware = datetime.now(UTC) - timedelta(days=STALE_DAYS + 1)
    fresh_aware = datetime.now(UTC)
    stale_naive = datetime.now() - timedelta(days=STALE_DAYS + 1)

    assert is_stale_by_last_worked(stale_aware) is True
    assert is_stale_by_last_worked(fresh_aware) is False
    assert is_stale_by_last_worked(stale_naive) is True


def test_resolve_last_worked_prefers_latest_activity():
    user = SimpleNamespace(id=1, username="agent")
    older = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    newer = datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    request = SimpleNamespace(
        updated_at=older,
        updated_by=user,
        request_workflows_live=[
            SimpleNamespace(
                started_at=older,
                started_by=user,
                ended_at=newer,
                completed_by=user,
                tasks=[
                    SimpleNamespace(
                        completed_at=newer,
                        completed_by=user,
                    )
                ],
            )
        ],
    )

    last_worked_at, last_worked_by = resolve_last_worked(request)

    assert last_worked_at == newer
    assert last_worked_by is user


def test_resolve_next_open_task_returns_first_open_task():
    request = SimpleNamespace(
        request_workflows_live=[
            SimpleNamespace(
                status=WORKFLOW_STATUS_ACTIVE,
                workflow_type_key=WORKFLOW_TYPE_RESEARCH,
                workflow_name="Research",
                tasks=[
                    SimpleNamespace(
                        id="10",
                        task_key="research_cruise_options",
                        task_title="Research cruise options",
                        status=TASK_STATUS_OPEN,
                        sequence_order=1,
                    ),
                    SimpleNamespace(
                        id="11",
                        task_key="upload_research_document",
                        task_title="Upload research document",
                        status=TASK_STATUS_OPEN,
                        sequence_order=2,
                    ),
                ],
            )
        ]
    )

    next_task = resolve_next_open_task(request)

    assert next_task is not None
    assert next_task.task_key == "research_cruise_options"
    assert next_task.workflow_name == "Research"


def test_resolve_next_open_task_returns_none_when_no_open_tasks():
    request = SimpleNamespace(
        request_workflows_live=[
            SimpleNamespace(
                status=WORKFLOW_STATUS_ACTIVE,
                workflow_type_key=WORKFLOW_TYPE_RESEARCH,
                workflow_name="Research",
                tasks=[
                    SimpleNamespace(
                        id="10",
                        task_key="research_cruise_options",
                        task_title="Research cruise options",
                        status="Done",
                        sequence_order=1,
                    )
                ],
            )
        ]
    )

    assert resolve_next_open_task(request) is None


def test_resolve_next_open_task_returns_none_without_active_workflow():
    request = SimpleNamespace(request_workflows_live=[])

    assert resolve_next_open_task(request) is None


def test_build_dashboard_open_request_includes_stale_and_next_task():
    user = SimpleNamespace(id=1, username="agent")
    fresh = datetime.now(UTC)
    request = SimpleNamespace(
        id=1,
        created_at=fresh,
        created_by=user,
        updated_at=fresh,
        updated_by=user,
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
        passengers=2,
        cabins_needed=1,
        status="Open",
        close_reason=None,
        request_workflows_live=[
            SimpleNamespace(
                status=WORKFLOW_STATUS_ACTIVE,
                workflow_type_key=WORKFLOW_TYPE_RESEARCH,
                workflow_name="Research",
                started_at=fresh,
                started_by=user,
                ended_at=None,
                completed_by=None,
                tasks=[
                    SimpleNamespace(
                        id="10",
                        task_key="research_cruise_options",
                        task_title="Research cruise options",
                        status=TASK_STATUS_OPEN,
                        sequence_order=1,
                        completed_at=None,
                        completed_by=None,
                    )
                ],
            )
        ],
    )

    dashboard_item = build_dashboard_open_request(request)

    assert dashboard_item.is_stale is False
    assert dashboard_item.next_open_task is not None
    assert dashboard_item.last_worked_by.username == "agent"
