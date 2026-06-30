from app.models import RequestTaskLive, RequestWorkflowLive
from app.schemas import RequestTaskRead, RequestWorkflowRead
from app.workflow_helpers import get_workflow_label


def task_to_read(task: RequestTaskLive) -> RequestTaskRead:
    prerequisite_keys: list[str] | None = None
    if task.template_task is not None and task.template_task.prerequisite_task_keys:
        prerequisite_keys = list(task.template_task.prerequisite_task_keys)

    return RequestTaskRead(
        id=task.id,
        task_key=task.task_key or "",
        title=task.task_title,
        description=task.description,
        status=task.status,
        sort_order=task.sequence_order,
        action_type=task.action_type,
        is_completed=task.is_completed,
        due_at=task.due_at,
        completed_at=task.completed_at,
        completed_by=task.completed_by,
        result=task.result,
        prerequisite_task_keys=prerequisite_keys,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def workflow_to_read(workflow: RequestWorkflowLive) -> RequestWorkflowRead:
    workflow_type = workflow.workflow_type_key or workflow.workflow_name
    return RequestWorkflowRead(
        id=workflow.id,
        workflow_type=workflow_type,
        workflow_name=workflow.workflow_name,
        status=workflow.status,
        parent_workflow_id=workflow.parent_workflow_live_id,
        context=workflow.context,
        started_by=workflow.started_by,
        completed_by=workflow.completed_by,
        tasks=[task_to_read(task) for task in sorted(workflow.tasks, key=lambda row: row.sequence_order)],
        created_at=workflow.started_at,
        updated_at=workflow.ended_at or workflow.started_at,
        completed_at=workflow.ended_at,
    )


def resolve_workflow_name(workflow: RequestWorkflowLive) -> str:
    if workflow.workflow_type_key:
        return get_workflow_label(workflow.workflow_type_key)
    return workflow.workflow_name
