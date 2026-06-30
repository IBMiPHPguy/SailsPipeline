from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import AgencyTaskTemplate, User
from app.schemas import (
    AgencyCustomTaskDefinitionCreate,
    AgencyCustomTaskDefinitionRead,
    AgencyCustomTaskDefinitionUpdate,
    AgencyTaskAvailabilityRead,
    AgencyTaskCatalogItemRead,
    AgencyTaskFromCatalogCreate,
    AgencyTaskFromCustomDefinitionCreate,
    AgencyTaskInventoryItemRead,
    AgencyTaskTemplateCreate,
    AgencyTaskTemplateMove,
    AgencyTaskTemplateMoveResult,
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
from app.services.agency_custom_task_service import (
    create_agency_custom_task_definition,
    create_agency_task_from_custom_definition,
    delete_agency_custom_task_definition,
    list_agency_custom_task_definitions,
    update_agency_custom_task_definition,
)
from app.services.agency_task_inventory_service import list_agency_task_inventory
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
    transfer_agency_task_to_workflow,
    update_agency_task_template,
    update_agency_workflow_template,
)

templates_router = APIRouter(prefix="/api/workflow-templates", tags=["workflow-templates"])
router = APIRouter(prefix="/api/requests", tags=["workflows"])
settings_router = APIRouter(prefix="/api/agency-workflow-templates", tags=["agency-workflow-templates"])
catalog_router = APIRouter(prefix="/api/agency-task-catalog", tags=["agency-task-catalog"])
custom_tasks_router = APIRouter(
    prefix="/api/agency-custom-task-definitions", tags=["agency-custom-task-definitions"]
)


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
    delete_agency_workflow_template(db, template_id=template_id, current_user=current_user)


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


@catalog_router.get("/inventory", response_model=list[AgencyTaskInventoryItemRead])
def list_agency_task_inventory_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> list[AgencyTaskInventoryItemRead]:
    items = list_agency_task_inventory(db, agency_id=current_user.agency_id)
    return [AgencyTaskInventoryItemRead.model_validate(item) for item in items]


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


@settings_router.post("/{template_id}/custom-tasks", response_model=AgencyWorkflowTemplateRead, status_code=201)
def create_agency_task_from_custom_definition_route(
    template_id: str,
    payload: AgencyTaskFromCustomDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    create_agency_task_from_custom_definition(
        db,
        template_id=template_id,
        task_key=payload.task_key,
        sequence_order=payload.sequence_order,
    )
    template = load_workflow_template(db, template_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@custom_tasks_router.get("", response_model=list[AgencyCustomTaskDefinitionRead])
def list_agency_custom_task_definitions_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> list[AgencyCustomTaskDefinitionRead]:
    definitions = list_agency_custom_task_definitions(db, agency_id=current_user.agency_id)
    return [AgencyCustomTaskDefinitionRead.model_validate(item) for item in definitions]


@custom_tasks_router.post("", response_model=AgencyCustomTaskDefinitionRead, status_code=201)
def create_agency_custom_task_definition_route(
    payload: AgencyCustomTaskDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyCustomTaskDefinitionRead:
    definition = create_agency_custom_task_definition(
        db,
        agency_id=current_user.agency_id,
        task_title=payload.task_title,
        description=payload.description,
    )
    return AgencyCustomTaskDefinitionRead.model_validate(definition)


@custom_tasks_router.patch("/{definition_id}", response_model=AgencyCustomTaskDefinitionRead)
def update_agency_custom_task_definition_route(
    definition_id: str,
    payload: AgencyCustomTaskDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyCustomTaskDefinitionRead:
    definition = update_agency_custom_task_definition(
        db,
        definition_id=definition_id,
        task_title=payload.task_title,
        description=payload.description,
    )
    return AgencyCustomTaskDefinitionRead.model_validate(definition)


@custom_tasks_router.delete("/{definition_id}", status_code=204)
def delete_agency_custom_task_definition_route(
    definition_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> None:
    delete_agency_custom_task_definition(db, definition_id=definition_id)


@settings_router.post("/{template_id}/catalog-tasks", response_model=AgencyWorkflowTemplateRead, status_code=201)
def create_agency_task_from_catalog_route(
    template_id: str,
    payload: AgencyTaskFromCatalogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyWorkflowTemplateRead:
    create_agency_task_from_catalog(
        db,
        template_id=template_id,
        task_key=payload.task_key,
        task_title=payload.task_title,
        sequence_order=payload.sequence_order,
    )
    template = load_workflow_template(db, template_id)
    return AgencyWorkflowTemplateRead.model_validate(template)


@settings_router.patch("/tasks/{task_id}/move", response_model=AgencyTaskTemplateMoveResult)
def transfer_agency_task_to_workflow_route(
    task_id: str,
    payload: AgencyTaskTemplateMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencyTaskTemplateMoveResult:
    source_template, target_template = transfer_agency_task_to_workflow(
        db,
        task_id=task_id,
        target_workflow_template_id=payload.target_workflow_template_id,
        sequence_order=payload.sequence_order,
    )
    return AgencyTaskTemplateMoveResult(
        source_workflow_template=AgencyWorkflowTemplateRead.model_validate(source_template),
        target_workflow_template=AgencyWorkflowTemplateRead.model_validate(target_template),
    )


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
    update_agency_task_template(
        db,
        task_id=task_id,
        task_title=payload.task_title,
        description=payload.description,
    )
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
