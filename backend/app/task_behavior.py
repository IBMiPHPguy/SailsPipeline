"""Task-scoped runtime behavior metadata decoupled from workflow_type_key."""

from __future__ import annotations

from dataclasses import dataclass

FOLLOW_UP_DUE_DAYS = 3
TASK_KEY_FOLLOW_UP_RESEARCH = "follow_up_research"
TASK_KEY_SEND_RESEARCH_COMMUNICATION = "send_research_communication"


@dataclass(frozen=True)
class TaskBehaviorMetadata:
    on_complete_schedule_follow_up_task_key: str | None = None
    follow_up_due_days: int = FOLLOW_UP_DUE_DAYS
    allows_reached_out: bool = False


TASK_BEHAVIOR_BY_KEY: dict[str, TaskBehaviorMetadata] = {
    TASK_KEY_SEND_RESEARCH_COMMUNICATION: TaskBehaviorMetadata(
        on_complete_schedule_follow_up_task_key=TASK_KEY_FOLLOW_UP_RESEARCH,
    ),
    TASK_KEY_FOLLOW_UP_RESEARCH: TaskBehaviorMetadata(allows_reached_out=True),
}


def get_task_behavior(task_key: str | None) -> TaskBehaviorMetadata | None:
    if not task_key:
        return None
    return TASK_BEHAVIOR_BY_KEY.get(task_key)


def task_behavior_to_catalog_fields(task_key: str) -> dict[str, object]:
    behavior = get_task_behavior(task_key)
    if behavior is None:
        return {}
    fields: dict[str, object] = {}
    if behavior.on_complete_schedule_follow_up_task_key:
        fields["on_complete_schedule_follow_up_task_key"] = behavior.on_complete_schedule_follow_up_task_key
        fields["follow_up_due_days"] = behavior.follow_up_due_days
    if behavior.allows_reached_out:
        fields["allows_reached_out"] = True
    return fields
