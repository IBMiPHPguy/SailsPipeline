from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.constants import TASK_STATUS_DONE, TASK_STATUS_OPEN, WORKFLOW_STATUS_ACTIVE, WORKFLOW_STATUS_COMPLETED
from app.models import RequestTaskLive, RequestWorkflowLive

TASK_KEY_ACCEPT_MASTER_TERMS = "accept_master_terms_and_conditions"


def sync_master_terms_tasks_for_request(db: Session, *, travel_request_id: int) -> int:
    """Complete open Master T&C tasks when the client already has an accepted agreement."""
    from app.constants import TC_STATUS_ACCEPTED
    from app.models import ClientTermsAgreement, TravelRequest
    from app.services.passenger_service import get_primary_passenger

    request = db.get(TravelRequest, travel_request_id)
    if request is None:
        return 0

    primary = get_primary_passenger(db, travel_request_id)
    if primary is None:
        return 0

    agreement = (
        db.query(ClientTermsAgreement)
        .filter(
            ClientTermsAgreement.agency_id == request.agency_id,
            ClientTermsAgreement.client_id == primary.passenger_id,
            ClientTermsAgreement.status == TC_STATUS_ACCEPTED,
        )
        .order_by(ClientTermsAgreement.accepted_at.desc())
        .first()
    )
    if agreement is None:
        return 0

    return complete_open_master_terms_tasks(
        db,
        travel_request_id=travel_request_id,
        accepted_at=agreement.accepted_at,
        source="master_terms_status_sync",
    )


def _maybe_auto_complete_workflow(workflow: RequestWorkflowLive, *, completed_at: datetime) -> None:
    if workflow.status != WORKFLOW_STATUS_ACTIVE or not workflow.tasks:
        return
    if not all(task.status == TASK_STATUS_DONE for task in workflow.tasks):
        return
    workflow.status = WORKFLOW_STATUS_COMPLETED
    workflow.completed_by_id = None
    workflow.ended_at = completed_at


def complete_open_master_terms_tasks(
    db: Session,
    *,
    travel_request_id: int,
    accepted_at: datetime,
    source: str = "master_terms_portal",
) -> int:
    """Mark open Master T&C tasks Done on active workflows for this request."""
    tasks = (
        db.query(RequestTaskLive)
        .join(RequestWorkflowLive, RequestWorkflowLive.id == RequestTaskLive.request_workflow_live_id)
        .filter(
            RequestTaskLive.travel_request_id == travel_request_id,
            RequestTaskLive.task_key == TASK_KEY_ACCEPT_MASTER_TERMS,
            RequestTaskLive.status == TASK_STATUS_OPEN,
            RequestWorkflowLive.status == WORKFLOW_STATUS_ACTIVE,
        )
        .all()
    )
    if not tasks:
        return 0

    workflow_ids: set[str] = set()
    for task in tasks:
        task.status = TASK_STATUS_DONE
        task.is_completed = True
        task.completed_at = accepted_at
        task.completed_by_id = None
        existing_result = dict(task.result or {})
        existing_result.update(
            {
                "master_terms_on_file": True,
                "accepted_at": accepted_at.isoformat(),
                "auto_completed": True,
                "completion_source": source,
            }
        )
        task.result = existing_result
        workflow_ids.add(task.request_workflow_live_id)

    for workflow_id in workflow_ids:
        workflow = db.get(RequestWorkflowLive, workflow_id)
        if workflow is not None:
            _maybe_auto_complete_workflow(workflow, completed_at=accepted_at)

    db.flush()
    return len(tasks)
