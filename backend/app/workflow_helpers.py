from dataclasses import dataclass
from datetime import datetime, timedelta

from app.constants import (
    TASK_STATUS_DONE,
    TASK_STATUS_OPEN,
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
    WORKFLOW_TYPE_ENTER_TRIP_CRM,
    WORKFLOW_TYPE_RESEARCH,
)
from app.task_behavior import get_task_behavior

FOLLOW_UP_DUE_DAYS = 3

TASK_KEY_SEND_RESEARCH_COMMUNICATION = "send_research_communication"
TASK_KEY_FOLLOW_UP_RESEARCH = "follow_up_research"
TASK_KEY_CLIENT_RESPONSE = "client_response"

COMMUNICATE_RESEARCH_PREREQUISITE_KEYS: dict[str, tuple[str, ...]] = {
    TASK_KEY_FOLLOW_UP_RESEARCH: (TASK_KEY_SEND_RESEARCH_COMMUNICATION,),
    TASK_KEY_CLIENT_RESPONSE: (TASK_KEY_SEND_RESEARCH_COMMUNICATION,),
}

WORKFLOW_SUCCESSORS: dict[str, str] = {
    WORKFLOW_TYPE_RESEARCH: WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
}


@dataclass(frozen=True)
class WorkflowTaskTemplate:
    task_key: str
    title: str
    description: str
    sort_order: int


WORKFLOW_DEFINITIONS: dict[str, dict[str, str]] = {
    WORKFLOW_TYPE_RESEARCH: {
        "name": "Research",
        "description": "Research cruise options, upload findings, and draft client communication.",
    },
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH: {
        "name": "Communicate Research",
        "description": "Send research findings to the client and track follow-up and response.",
    },
    WORKFLOW_TYPE_ENTER_TRIP_CRM: {
        "name": "Enter Trip in CRM",
        "description": "Verify passenger details and complete CRM booking checklist.",
    },
}

WORKFLOW_TASK_TEMPLATES: dict[str, list[WorkflowTaskTemplate]] = {
    WORKFLOW_TYPE_RESEARCH: [
        WorkflowTaskTemplate(
            "research_cruise_options",
            "Research cruise options",
            "Research cruise options for this request.",
            1,
        ),
        WorkflowTaskTemplate(
            "upload_research_document",
            "Upload research document",
            "Upload the text research document created for this request.",
            2,
        ),
        WorkflowTaskTemplate(
            "create_proposed_cruises",
            "Create proposed cruises",
            "Add proposed cruises based on the research findings.",
            3,
        ),
        WorkflowTaskTemplate(
            "draft_research_communication",
            "Draft research communication",
            "Create the client communication summarizing the research findings.",
            4,
        ),
    ],
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH: [
        WorkflowTaskTemplate(
            "send_research_communication",
            "Send research communication",
            "Send the research communication to the client and mark it as sent.",
            1,
        ),
        WorkflowTaskTemplate(
            "follow_up_research",
            "Follow up on research communication",
            "Follow up with the client three days after the research communication was sent.",
            2,
        ),
        WorkflowTaskTemplate(
            "client_response",
            "Record client response",
            "Record whether the client accepted a proposed cruise, rejected all options, or needs more research.",
            3,
        ),
    ],
    WORKFLOW_TYPE_ENTER_TRIP_CRM: [
        WorkflowTaskTemplate(
            "accept_master_terms_and_conditions",
            "Master Terms & Conditions",
            "Verify or collect the client's signed Master Terms & Conditions before continuing.",
            1,
        ),
        WorkflowTaskTemplate(
            "verify_passenger_details",
            "Verify passenger details",
            "Verify names, dates of birth, and contact information for each passenger.",
            2,
        ),
        WorkflowTaskTemplate(
            "collect_passenger_addresses",
            "Collect passenger addresses",
            "Collect the primary passenger's home address. Other passenger addresses are optional.",
            3,
        ),
        WorkflowTaskTemplate(
            "create_cabin_holds",
            "Create cabin holds with cruise lines",
            "Enter cruise line reservation IDs for each cabin on this request.",
            4,
        ),
        WorkflowTaskTemplate(
            "verify_travel_insurance",
            "Travel insurance validation",
            "Confirm annual insurance coverage or verify per-trip insurance quotes and waiver compliance.",
            5,
        ),
        WorkflowTaskTemplate(
            "collect_payment_and_send_booking_communication",
            "Collect deposit or final payment and send cruise line communications",
            "Collect payment for each cabin hold, send booking communications, then mark this task done.",
            6,
        ),
        WorkflowTaskTemplate(
            "create_trip_in_crm",
            "Enter Trip in CRM",
            "Create the trip and bookings in your agency CRM, send the agency invoice, then check off each step below.",
            7,
        ),
    ],
}


def get_workflow_label(workflow_type: str) -> str:
    return WORKFLOW_DEFINITIONS.get(workflow_type, {}).get("name", workflow_type)


def get_task_templates(workflow_type: str) -> list[WorkflowTaskTemplate]:
    return WORKFLOW_TASK_TEMPLATES.get(workflow_type, [])


def get_successor_workflow_type(workflow_type: str) -> str | None:
    return WORKFLOW_SUCCESSORS.get(workflow_type)


def _task_by_key(tasks: list, task_key: str):
    return next(
        (
            task
            for task in tasks
            if (getattr(task, "task_key", None) or "") == task_key
        ),
        None,
    )


def get_workflow_type_key(workflow) -> str | None:
    return getattr(workflow, "workflow_type_key", None) or getattr(workflow, "workflow_type", None)


def schedule_follow_up_due_date(
    workflow,
    completed_at: datetime,
    *,
    completed_task_key: str = TASK_KEY_SEND_RESEARCH_COMMUNICATION,
) -> None:
    behavior = get_task_behavior(completed_task_key)
    if behavior is None or not behavior.on_complete_schedule_follow_up_task_key:
        return

    follow_up = _task_by_key(workflow.tasks, behavior.on_complete_schedule_follow_up_task_key)
    if follow_up is None or follow_up.status != TASK_STATUS_OPEN:
        return

    follow_up.due_at = completed_at + timedelta(days=behavior.follow_up_due_days)


def apply_task_completion_side_effects(workflow, completed_task) -> None:
    behavior = get_task_behavior(getattr(completed_task, "task_key", None))
    if behavior is None or not behavior.on_complete_schedule_follow_up_task_key:
        return
    if getattr(completed_task, "status", None) != TASK_STATUS_DONE:
        return
    completed_at = getattr(completed_task, "completed_at", None)
    if completed_at is None:
        return

    follow_up = _task_by_key(workflow.tasks, behavior.on_complete_schedule_follow_up_task_key)
    if follow_up is None or follow_up.status != TASK_STATUS_OPEN:
        return

    follow_up.due_at = completed_at + timedelta(days=behavior.follow_up_due_days)


def ensure_follow_up_due_date(workflow) -> None:
    for task in workflow.tasks:
        if task.status != TASK_STATUS_DONE or task.completed_at is None:
            continue
        behavior = get_task_behavior(task.task_key)
        if behavior is None or not behavior.on_complete_schedule_follow_up_task_key:
            continue

        follow_up = _task_by_key(workflow.tasks, behavior.on_complete_schedule_follow_up_task_key)
        if follow_up is None:
            continue
        if follow_up.status != TASK_STATUS_OPEN or follow_up.due_at is not None:
            continue

        follow_up.due_at = task.completed_at + timedelta(days=behavior.follow_up_due_days)


def record_follow_up_reached_out(task, *, now: datetime) -> None:
    behavior = get_task_behavior(task.task_key)
    if behavior is None or not behavior.allows_reached_out:
        raise ValueError("Reached out can only be recorded on tasks that support follow-up outreach.")
    if task.status != TASK_STATUS_OPEN:
        raise ValueError("Reached out can only be recorded on open tasks.")

    result = dict(task.result or {})
    history = list(result.get("reached_out_history", []))
    history.append(now.isoformat())
    result["reached_out_history"] = history
    result["last_reached_out_at"] = now.isoformat()
    task.result = result
    task.due_at = now + timedelta(days=FOLLOW_UP_DUE_DAYS)
