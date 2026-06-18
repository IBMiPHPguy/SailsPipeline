from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import RequestWorkflow, User
from app.schemas import RequestTaskUpdate, RequestWorkflowCreate, RequestWorkflowRead, RequestWorkflowUpdate, WorkflowTemplateRead
from app.services.workflow_service import (
    list_workflow_templates,
    start_workflow,
    update_task,
    update_workflow,
)

templates_router = APIRouter(prefix="/api/workflow-templates", tags=["workflow-templates"])
router = APIRouter(prefix="/api/requests", tags=["workflows"])


@templates_router.get("", response_model=list[WorkflowTemplateRead])
def list_workflow_templates_route(_: User = Depends(get_current_user)) -> list[WorkflowTemplateRead]:
    return list_workflow_templates()


@router.post("/{request_id}/workflows", response_model=RequestWorkflowRead, status_code=201)
def start_workflow_route(
    request_id: int,
    payload: RequestWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflow:
    return start_workflow(db, request_id=request_id, payload=payload, current_user=current_user)


@router.patch("/{request_id}/workflows/{workflow_id}", response_model=RequestWorkflowRead)
def update_workflow_route(
    request_id: int,
    workflow_id: int,
    payload: RequestWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflow:
    return update_workflow(
        db,
        request_id=request_id,
        workflow_id=workflow_id,
        payload=payload,
        current_user=current_user,
    )


@router.patch("/{request_id}/tasks/{task_id}", response_model=RequestWorkflowRead)
def update_task_route(
    request_id: int,
    task_id: int,
    payload: RequestTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflow:
    return update_task(
        db,
        request_id=request_id,
        task_id=task_id,
        payload=payload,
        current_user=current_user,
    )
