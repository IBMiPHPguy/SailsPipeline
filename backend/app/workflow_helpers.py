from dataclasses import dataclass
from datetime import datetime, timedelta

from app.constants import (
    TASK_STATUS_DONE,
    TASK_STATUS_OPEN,
    WORKFLOW_TYPE_COMMUNICATE_RESEARCH,
    WORKFLOW_TYPE_ENTER_TRIP_CRM,
    WORKFLOW_TYPE_RESEARCH,
)

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
            "verify_passenger_details",
            "Verify passenger details",
            "Verify names, dates of birth, and contact information for each passenger.",
            1,
        ),
        WorkflowTaskTemplate(
            "collect_passenger_addresses",
            "Collect passenger addresses",
            "Collect the primary passenger's home address. Other passenger addresses are optional.",
            2,
        ),
        WorkflowTaskTemplate(
            "create_cabin_holds",
            "Create cabin holds with cruise lines",
            "Enter cruise line reservation IDs for each cabin on this request.",
            3,
        ),
        WorkflowTaskTemplate(
            "collect_payment_and_send_booking_communication",
            "Collect deposit or final payment and send cruise line communications",
            "Collect payment for each cabin hold, send booking communications, then mark this task done.",
            4,
        ),
        WorkflowTaskTemplate(
            "create_trip_in_crm",
            "Enter Trip in CRM",
            "Create the trip and bookings in your agency CRM, send the agency invoice, then check off each step below.",
            5,
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


def schedule_follow_up_due_date(workflow, send_completed_at: datetime) -> None:
    follow_up = _task_by_key(workflow.tasks, TASK_KEY_FOLLOW_UP_RESEARCH)
    if follow_up is None or follow_up.status != TASK_STATUS_OPEN:
        return

    follow_up.due_at = send_completed_at + timedelta(days=FOLLOW_UP_DUE_DAYS)


def ensure_follow_up_due_date(workflow) -> None:
    send_task = _task_by_key(workflow.tasks, TASK_KEY_SEND_RESEARCH_COMMUNICATION)
    follow_up = _task_by_key(workflow.tasks, TASK_KEY_FOLLOW_UP_RESEARCH)
    if send_task is None or follow_up is None:
        return
    if send_task.status != TASK_STATUS_DONE or follow_up.status != TASK_STATUS_OPEN or follow_up.due_at is not None:
        return
    if send_task.completed_at is None:
        return

    follow_up.due_at = send_task.completed_at + timedelta(days=FOLLOW_UP_DUE_DAYS)


def record_follow_up_reached_out(task, *, now: datetime) -> None:
    if task.task_key != TASK_KEY_FOLLOW_UP_RESEARCH:
        raise ValueError("Reached out can only be recorded on follow-up tasks.")
    if task.status != TASK_STATUS_OPEN:
        raise ValueError("Reached out can only be recorded on open tasks.")

    result = dict(task.result or {})
    history = list(result.get("reached_out_history", []))
    history.append(now.isoformat())
    result["reached_out_history"] = history
    result["last_reached_out_at"] = now.isoformat()
    task.result = result
    task.due_at = now + timedelta(days=FOLLOW_UP_DUE_DAYS)
