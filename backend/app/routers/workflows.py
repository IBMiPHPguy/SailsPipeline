from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import AgencyTaskTemplate, User
from app.schemas import (
    AgencyTaskAvailabilityRead,
    AgencyTaskCatalogItemRead,
    AgencyTaskFromCatalogCreate,
    AgencyTaskTemplateCreate,
    AgencyTaskTemplateRead,
    AgencyTaskTemplateUpdate,
    AgencyWorkflowTemplateCreate,
    AgencyWorkflowTemplateRead,
    AgencyWorkflowTemplateUpdate,
    RequestTaskUpdate,
    RequestWorkflowCreate,
    RequestWorkflowRead,
    RequestWorkflowUpdate,
    WorkflowTemplateRead,
)
from app.services.workflow_task_catalog_service import (
    build_system_task_catalog,
    get_agency_task_availability,
)
from app.services.workflow_read import workflow_to_read
from app.services.workflow_service import (
    list_workflow_templates,
    start_workflow,
    update_task,
    update_workflow,
)
from app.services.workflow_template_service import (
    create_agency_task_from_catalog,
    create_agency_task_template,
    create_agency_workflow_template,
    delete_agency_task_template,
    delete_agency_workflow_template,
    list_agency_workflow_templates,
    load_workflow_template,
    move_agency_task_template,
    update_agency_task_template,
    update_agency_workflow_template,
)

templates_router = APIRouter(prefix="/api/workflow-templates", tags=["workflow-templates"])
router = APIRouter(prefix="/api/requests", tags=["workflows"])
settings_router = APIRouter(prefix="/api/agency-workflow-templates", tags=["agency-workflow-templates"])
catalog_router = APIRouter(prefix="/api/agency-task-catalog", tags=["agency-task-catalog"])


@templates_router.get("", response_model=list[WorkflowTemplateRead])
def list_workflow_templates_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkflowTemplateRead]:
    if current_user.agency_id is None:
        return []
    return list_workflow_templates(db, agency_id=current_user.agency_id)


@router.post("/{request_id}/workflows", response_model=RequestWorkflowRead, status_code=201)
def start_workflow_route(
    request_id: int,
    payload: RequestWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflowRead:
    workflow = start_workflow(db, request_id=request_id, payload=payload, current_user=current_user)
    return workflow_to_read(workflow)


@router.patch("/{request_id}/workflows/{workflow_id}", response_model=RequestWorkflowRead)
def update_workflow_route(
    request_id: int,
    workflow_id: str,
    payload: RequestWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflowRead:
    workflow = update_workflow(
        db,
        request_id=request_id,
        workflow_id=workflow_id,
        payload=payload,
        current_user=current_user,
    )
    return workflow_to_read(workflow)


@router.patch("/{request_id}/tasks/{task_id}", response_model=RequestWorkflowRead)
def update_task_route(
    request_id: int,
    task_id: str,
    payload: RequestTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestWorkflowRead:
    workflow = update_task(
        db,
        request_id=request_id,
        task_id=task_id,
        payload=payload,
        current_user=current_user,
    )
    return workflow_to_read(workflow)


@settings_router.get("", response_model=list[AgencyWorkflowTemplateRead])
def list_agency_workflow_templates_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> list[AgencyWorkflowTemplateRead]:
    templates = list_agency_workflow_templates(db, agency_id=current_user.agency_id)
    return [AgencyWorkflowTemplateRead.model_validate(template) for template in templates]


@settings_router.post("", response_model=AgencyWorkflowTemplateRead, status_code=201)
def create_agency_workflow_template_route(
    payload: AgencyWorkflowTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    template = create_agency_workflow_template(
        db,
        agency_id=current_user.agency_id,
        workflow_name=payload.workflow_name,
        description=payload.description,
    )
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.patch("/{template_id}", response_model=AgencyWorkflowTemplateRead)
def update_agency_workflow_template_route(
    template_id: str,
    payload: AgencyWorkflowTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    template = update_agency_workflow_template(
        db,
        template_id=template_id,
        workflow_name=payload.workflow_name,
        description=payload.description,
    )
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.delete("/{template_id}", status_code=204)
def delete_agency_workflow_template_route(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> None:
    delete_agency_workflow_template(db, template_id=template_id)


@catalog_router.get("", response_model=list[AgencyTaskCatalogItemRead])
def list_agency_task_catalog_route(
    _current_user: User = Depends(require_tenant_super_user),
) -> list[AgencyTaskCatalogItemRead]:
    return [AgencyTaskCatalogItemRead.model_validate(item) for item in build_system_task_catalog()]


@catalog_router.get("/availability", response_model=AgencyTaskAvailabilityRead)
def get_agency_task_availability_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyTaskAvailabilityRead:
    payload = get_agency_task_availability(db, agency_id=current_user.agency_id)
    return AgencyTaskAvailabilityRead.model_validate(payload)


@settings_router.post("/{template_id}/tasks", response_model=AgencyWorkflowTemplateRead, status_code=201)
def create_agency_task_template_route(
    template_id: str,
    payload: AgencyTaskTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    create_agency_task_template(db, template_id=template_id, task_title=payload.task_title)
    template = load_workflow_template(db, template_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.post("/{template_id}/catalog-tasks", response_model=AgencyWorkflowTemplateRead, status_code=201)
def create_agency_task_from_catalog_route(
    template_id: str,
    payload: AgencyTaskFromCatalogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    create_agency_task_from_catalog(db, template_id=template_id, task_key=payload.task_key)
    template = load_workflow_template(db, template_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.patch("/tasks/{task_id}", response_model=AgencyWorkflowTemplateRead)
def update_agency_task_template_route(
    task_id: str,
    payload: AgencyTaskTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    task = db.get(AgencyTaskTemplate, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task template not found.")
    update_agency_task_template(db, task_id=task_id, task_title=payload.task_title)
    template = load_workflow_template(db, task.workflow_template_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.delete("/tasks/{task_id}", response_model=AgencyWorkflowTemplateRead)
def delete_agency_task_template_route(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    template = delete_agency_task_template(db, task_id=task_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.post("/tasks/{task_id}/move/{direction}", response_model=AgencyWorkflowTemplateRead)
def move_agency_task_template_route(
    task_id: str,
    direction: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    template = move_agency_task_template(db, task_id=task_id, direction=direction)
    return AgencyWorkflowTemplateRead.model_validate(template)
