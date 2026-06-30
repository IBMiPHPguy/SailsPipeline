from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.constants import WORKFLOW_TYPE_COMMUNICATE_RESEARCH, WORKFLOW_TYPE_RESEARCH
from app.proposed_cruise_helpers import (
    flatten_room_passenger_ids,
    normalize_cabin_pricing_list,
    normalize_cabin_rooms_list,
    normalize_room_passenger_ids,
)
from app.schemas import normalize_cruise_line_value
from app.workflow_helpers import (
    TASK_KEY_FOLLOW_UP_RESEARCH,
    TASK_KEY_SEND_RESEARCH_COMMUNICATION,
    ensure_follow_up_due_date,
    get_successor_workflow_type,
    get_task_templates,
    get_workflow_label,
    record_follow_up_reached_out,
    schedule_follow_up_due_date,
)


def test_get_workflow_label_known_type():
    assert get_workflow_label(WORKFLOW_TYPE_RESEARCH) == "Research"


def test_get_workflow_label_unknown_type():
    assert get_workflow_label("custom_workflow") == "custom_workflow"


def test_get_successor_workflow_type():
    assert get_successor_workflow_type(WORKFLOW_TYPE_RESEARCH) == WORKFLOW_TYPE_COMMUNICATE_RESEARCH
    assert get_successor_workflow_type(WORKFLOW_TYPE_COMMUNICATE_RESEARCH) is None


def test_get_task_templates_research_workflow():
    templates = get_task_templates(WORKFLOW_TYPE_RESEARCH)
    assert [task.task_key for task in templates] == [
        "research_cruise_options",
        "upload_research_document",
        "create_proposed_cruises",
        "draft_research_communication",
    ]


def test_schedule_follow_up_due_date():
    send_completed_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    class Task:
        def __init__(self, task_key, status):
            self.task_key = task_key
            self.status = status
            self.due_at = None

    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = [
            Task(TASK_KEY_SEND_RESEARCH_COMMUNICATION, "Done"),
            Task(TASK_KEY_FOLLOW_UP_RESEARCH, "Open"),
        ]

    workflow = Workflow()
    schedule_follow_up_due_date(workflow, send_completed_at)
    assert workflow.tasks[1].due_at == send_completed_at + timedelta(days=3)


def test_ensure_follow_up_due_date_from_completed_send_task():
    completed_at = datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc)

    class Task:
        def __init__(self, task_key, status, completed_at=None, due_at=None):
            self.task_key = task_key
            self.status = status
            self.completed_at = completed_at
            self.due_at = due_at

    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = [
            Task(TASK_KEY_SEND_RESEARCH_COMMUNICATION, "Done", completed_at=completed_at),
            Task(TASK_KEY_FOLLOW_UP_RESEARCH, "Open"),
        ]

    workflow = Workflow()
    ensure_follow_up_due_date(workflow)
    assert workflow.tasks[1].due_at == completed_at + timedelta(days=3)


def test_record_follow_up_reached_out_appends_history():
    now = datetime(2026, 6, 4, 15, 0, tzinfo=timezone.utc)

    class Task:
        task_key = TASK_KEY_FOLLOW_UP_RESEARCH
        status = "Open"
        result = {}
        due_at = None

    task = Task()
    record_follow_up_reached_out(task, now=now)
    assert task.result["last_reached_out_at"] == now.isoformat()
    assert task.result["reached_out_history"] == [now.isoformat()]
    assert task.due_at == now + timedelta(days=3)


def test_record_follow_up_reached_out_rejects_wrong_task_key():
    class Task:
        task_key = "other_task"
        status = "Open"
        result = {}

    with pytest.raises(ValueError, match="follow-up outreach"):
        record_follow_up_reached_out(Task(), now=datetime.now(timezone.utc))


def test_record_follow_up_reached_out_rejects_non_open_task():
    class Task:
        task_key = TASK_KEY_FOLLOW_UP_RESEARCH
        status = "Done"
        result = {}

    with pytest.raises(ValueError, match="open tasks"):
        record_follow_up_reached_out(Task(), now=datetime.now(timezone.utc))


def test_schedule_follow_up_due_date_ignores_when_follow_up_task_missing():
    class Task:
        task_key = TASK_KEY_SEND_RESEARCH_COMMUNICATION
        status = "Open"
        due_at = None

    class Workflow:
        workflow_type = WORKFLOW_TYPE_RESEARCH
        tasks = [Task()]

    workflow = Workflow()
    schedule_follow_up_due_date(workflow, datetime(2026, 6, 1, tzinfo=timezone.utc))
    assert workflow.tasks[0].due_at is None


def test_ensure_follow_up_due_date_ignores_when_follow_up_already_scheduled():
    completed_at = datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc)

    class Task:
        def __init__(self, task_key, status, completed_at=None, due_at=None):
            self.task_key = task_key
            self.status = status
            self.completed_at = completed_at
            self.due_at = due_at

    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = [
            Task(TASK_KEY_SEND_RESEARCH_COMMUNICATION, "Done", completed_at=completed_at),
            Task(TASK_KEY_FOLLOW_UP_RESEARCH, "Open", due_at=completed_at),
        ]

    workflow = Workflow()
    ensure_follow_up_due_date(workflow)
    assert workflow.tasks[1].due_at == completed_at


def test_schedule_follow_up_due_date_skips_when_follow_up_not_open():
    send_completed_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)

    class Task:
        def __init__(self, task_key, status):
            self.task_key = task_key
            self.status = status
            self.due_at = None

    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = [
            Task(TASK_KEY_SEND_RESEARCH_COMMUNICATION, "Done"),
            Task(TASK_KEY_FOLLOW_UP_RESEARCH, "Done"),
        ]

    workflow = Workflow()
    schedule_follow_up_due_date(workflow, send_completed_at)
    assert workflow.tasks[1].due_at is None


def test_ensure_follow_up_due_date_ignores_non_communicate_workflow():
    class Task:
        task_key = TASK_KEY_FOLLOW_UP_RESEARCH
        status = "Open"
        completed_at = None
        due_at = None

    class Workflow:
        workflow_type = WORKFLOW_TYPE_RESEARCH
        tasks = [Task()]

    workflow = Workflow()
    ensure_follow_up_due_date(workflow)
    assert workflow.tasks[0].due_at is None


def test_ensure_follow_up_due_date_ignores_missing_tasks():
    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = []

    ensure_follow_up_due_date(Workflow())


def test_ensure_follow_up_due_date_ignores_send_without_completed_at():
    class Task:
        def __init__(self, task_key, status, completed_at=None, due_at=None):
            self.task_key = task_key
            self.status = status
            self.completed_at = completed_at
            self.due_at = due_at

    class Workflow:
        workflow_type = WORKFLOW_TYPE_COMMUNICATE_RESEARCH
        tasks = [
            Task(TASK_KEY_SEND_RESEARCH_COMMUNICATION, "Done", completed_at=None),
            Task(TASK_KEY_FOLLOW_UP_RESEARCH, "Open"),
        ]

    workflow = Workflow()
    ensure_follow_up_due_date(workflow)
    assert workflow.tasks[1].due_at is None


def test_normalize_cabin_pricing_uses_existing_entries():
    pricing = normalize_cabin_pricing_list(
        [{"deposit_amount": "75.00", "cost": "1500.00"}],
        2,
        deposit_amount=Decimal("100.00"),
        cost=Decimal("2000.00"),
    )
    assert pricing[0] == {"deposit_amount": "75.00", "cost": "1500.00"}
    assert pricing[1] == {"deposit_amount": "50.00", "cost": "1000.00"}


def test_normalize_cabin_pricing_splits_totals_evenly():
    pricing = normalize_cabin_pricing_list(
        None,
        2,
        deposit_amount=Decimal("100.00"),
        cost=Decimal("2000.00"),
    )
    assert pricing == [
        {"deposit_amount": "50.00", "cost": "1000.00"},
        {"deposit_amount": "50.00", "cost": "1000.00"},
    ]


def test_normalize_cabin_rooms_preserves_existing_room_and_fills_missing():
    includes = {
        "drink_package": {"included": False, "name": ""},
        "wifi": {"included": False, "name": ""},
        "tips": False,
        "excursion": False,
        "excursion_credit": {"included": False, "amount": None},
        "onboard_credit": {"included": False, "amount": None},
        "gift_obc": {"included": False, "amount": None},
    }
    rooms = normalize_cabin_rooms_list(
        [
            {
                "room_category": "Suite",
                "room_number": "9001",
                "passengers_in_room": 2,
                "deposit_amount": "250.00",
                "commission": "50.00",
                "cost": "5000.00",
                "includes": includes,
            }
        ],
        2,
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("500.00"),
        cost=Decimal("10000.00"),
        includes=includes,
        cabin_pricing=None,
    )
    assert len(rooms) == 2
    assert rooms[0]["room_category"] == "Suite"
    assert rooms[1]["room_category"] == "Balcony"
    assert rooms[1]["deposit_amount"] == "250.00"


def test_normalize_room_passenger_ids_from_flat_list():
    assert normalize_room_passenger_ids(None, [10, 11], 2) == [[10, 11], []]


def test_normalize_room_passenger_ids_from_nested_lists():
    assert normalize_room_passenger_ids([[1], [2, 3]], None, 3) == [[1], [2, 3], []]


def test_flatten_room_passenger_ids():
    assert flatten_room_passenger_ids([[1, 2], [3]]) == [1, 2, 3]


def test_normalize_cruise_line_value_matches_canonical_name():
    assert normalize_cruise_line_value("royal caribbean") == "Royal Caribbean International"


def test_normalize_cruise_line_value_rejects_unknown_without_match():
    assert normalize_cruise_line_value("Unknown Line XYZ") == "Unknown Line XYZ"
