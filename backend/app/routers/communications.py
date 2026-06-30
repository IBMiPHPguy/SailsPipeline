from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import RequestCommunication, User
from app.schemas import (
    GenerateResearchCommunicationRequest,
    GenerateResearchCommunicationResponse,
    RequestCommunicationCreate,
    RequestCommunicationRead,
    RequestCommunicationUpdate,
)
from app.services.agency_service import (
    assert_child_belongs_to_request,
    get_travel_request_for_agency,
    require_record_for_agency,
)
from app.services.communication_service import (
    create_communication,
    delete_draft_communication,
    generate_research_communication_from_proposed_cruises,
    load_communication,
    update_communication_record,
)
from app.services.request_service import get_open_request
from app.tenant_context import require_current_agency_id

router = APIRouter(prefix="/api/requests", tags=["communications"])


def _load_communication_for_request(
    db: Session,
    *,
    request_id: int,
    communication_id: int,
) -> RequestCommunication:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    communication = (
        db.query(RequestCommunication)
        .options(
            joinedload(RequestCommunication.created_by),
            joinedload(RequestCommunication.updated_by),
        )
        .filter(
            RequestCommunication.id == communication_id,
            RequestCommunication.travel_request_id == request_id,
        )
        .first()
    )
    require_record_for_agency(communication, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=communication.agency_id,
        child_travel_request_id=communication.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )
    return communication


@router.get("/{request_id}/communications/{communication_id}", response_model=RequestCommunicationRead)
def get_communication(
    request_id: int,
    communication_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RequestCommunication:
    return _load_communication_for_request(db, request_id=request_id, communication_id=communication_id)


@router.post(
    "/{request_id}/communications/generate-from-proposals",
    response_model=GenerateResearchCommunicationResponse,
)
def generate_research_communication_from_proposed_cruises_route(
    request_id: int,
    payload: GenerateResearchCommunicationRequest = Body(default_factory=GenerateResearchCommunicationRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateResearchCommunicationResponse:
    request = get_open_request(db, request_id)
    return generate_research_communication_from_proposed_cruises(
        db,
        request=request,
        current_user=current_user,
        request_workflow_live_id=payload.request_workflow_id,
    )


@router.post(
    "/{request_id}/communications",
    response_model=RequestCommunicationRead,
    status_code=201,
)
def add_communication(
    request_id: int,
    payload: RequestCommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestCommunication:
    request = get_open_request(db, request_id)
    return create_communication(
        db,
        request=request,
        current_user=current_user,
        request_id=request_id,
        request_workflow_live_id=payload.request_workflow_id,
        communication_type=payload.communication_type,
        subject=payload.subject,
        body=payload.body,
        status=payload.status,
    )


@router.patch(
    "/{request_id}/communications/{communication_id}",
    response_model=RequestCommunicationRead,
)
def update_communication(
    request_id: int,
    communication_id: int,
    payload: RequestCommunicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestCommunication:
    request = get_open_request(db, request_id)
    communication = _load_communication_for_request(
        db,
        request_id=request_id,
        communication_id=communication_id,
    )

    return update_communication_record(
        db,
        request=request,
        communication=communication,
        current_user=current_user,
        updates=payload.model_dump(exclude_unset=True),
    )


@router.delete("/{request_id}/communications/{communication_id}", status_code=204)
def delete_communication(
    request_id: int,
    communication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    request = get_open_request(db, request_id)
    communication = _load_communication_for_request(
        db,
        request_id=request_id,
        communication_id=communication_id,
    )

    delete_draft_communication(
        db,
        request=request,
        communication=communication,
        current_user=current_user,
    )
