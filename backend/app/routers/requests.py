from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    CallTranscript,
    ChatLog,
    QuotedInsurance,
    RequestNote,
    RequestResearchDocument,
    TravelRequest,
    User,
)
from app.schemas import (
    AttachmentRead,
    BulkProposedCruiseCreate,
    BulkProposedCruiseCreateResponse,
    GenerateProposedCruisesRequest,
    GenerateProposedCruisesResponse,
    ProposedCruiseCreate,
    ProposedCruiseRead,
    ProposedCruiseUpdate,
    QuotedInsuranceCreate,
    QuotedInsuranceRead,
    QuotedInsuranceUpdate,
    RequestChangeHistoryRead,
    RequestNoteCreate,
    RequestNoteRead,
    RequestNoteUpdate,
    ResearchDocumentRead,
    ClosedRequestsPageRead,
    OpenRequestsPageRead,
    TravelRequestCreate,
    TravelRequestDetailRead,
    TravelRequestRead,
    TravelRequestUpdate,
)
from app.services.note_service import add_note, get_request_note, list_request_notes, update_note
from app.services.proposed_cruise_record_service import (
    add_proposed_cruise,
    add_proposed_cruises_bulk,
    generate_proposed_cruises_from_research_document,
    update_proposed_cruise,
)
from app.services.quoted_insurance_service import add_quoted_insurance, update_quoted_insurance
from app.services.request_attachment_service import (
    add_chat_log,
    add_transcript,
    get_chat_log_content,
    get_research_document_content,
    get_transcript_content,
    upload_research_document,
)
from app.services.request_service import (
    create_request,
    get_request_change_history,
    get_request_detail,
    closed_requests_total_pages,
    search_closed_requests,
    search_open_requests,
    list_requests,
    reopen_request,
    update_request,
)

router = APIRouter(prefix="/api/requests", tags=["requests"])


@router.get("", response_model=list[TravelRequestRead])
def list_requests_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[TravelRequest]:
    return list_requests(db)


@router.get("/open", response_model=OpenRequestsPageRead)
def list_open_requests_route(
    q: str = "",
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> OpenRequestsPageRead:
    normalized_page_size = max(1, min(page_size, 100))
    items, total = search_open_requests(db, query=q, page=page, page_size=normalized_page_size)
    return OpenRequestsPageRead(
        items=items,
        total=total,
        page=max(1, page),
        page_size=normalized_page_size,
        total_pages=closed_requests_total_pages(total, normalized_page_size),
    )


@router.get("/closed", response_model=ClosedRequestsPageRead)
def list_closed_requests_route(
    q: str = "",
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClosedRequestsPageRead:
    normalized_page_size = max(1, min(page_size, 100))
    items, total = search_closed_requests(db, query=q, page=page, page_size=normalized_page_size)
    return ClosedRequestsPageRead(
        items=items,
        total=total,
        page=max(1, page),
        page_size=normalized_page_size,
        total_pages=closed_requests_total_pages(total, normalized_page_size),
    )


@router.post("/{request_id}/reopen", response_model=TravelRequestRead)
def reopen_request_route(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TravelRequest:
    return reopen_request(db, request_id, current_user)


@router.post("", response_model=TravelRequestRead, status_code=201)
def create_request_route(
    payload: TravelRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TravelRequest:
    return create_request(db, payload, current_user)


@router.get("/{request_id}", response_model=TravelRequestDetailRead)
def get_request_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TravelRequestDetailRead:
    return get_request_detail(db, request_id)


@router.get("/{request_id}/change-history", response_model=RequestChangeHistoryRead)
def get_request_change_history_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RequestChangeHistoryRead:
    return get_request_change_history(db, request_id)


@router.get("/{request_id}/notes", response_model=list[RequestNoteRead])
def list_request_notes_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[RequestNote]:
    return list_request_notes(db, request_id)


@router.get("/{request_id}/notes/{note_id}", response_model=RequestNoteRead)
def get_request_note_route(
    request_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> RequestNote:
    return get_request_note(db, request_id, note_id)


@router.patch("/{request_id}", response_model=TravelRequestDetailRead)
def update_request_route(
    request_id: int,
    payload: TravelRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TravelRequestDetailRead:
    return update_request(db, request_id=request_id, payload=payload, current_user=current_user)


@router.post("/{request_id}/transcripts", response_model=AttachmentRead, status_code=201)
async def add_transcript_route(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CallTranscript:
    return await add_transcript(db, request_id=request_id, file=file, current_user=current_user)


@router.get("/{request_id}/transcripts/{transcript_id}/content")
def get_transcript_content_route(
    request_id: int,
    transcript_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PlainTextResponse:
    return get_transcript_content(db, request_id, transcript_id)


@router.post("/{request_id}/chats", response_model=AttachmentRead, status_code=201)
async def add_chat_log_route(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatLog:
    return await add_chat_log(db, request_id=request_id, file=file, current_user=current_user)


@router.get("/{request_id}/chats/{chat_id}/content")
def get_chat_log_content_route(
    request_id: int,
    chat_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PlainTextResponse:
    return get_chat_log_content(db, request_id, chat_id)


@router.post("/{request_id}/notes", response_model=RequestNoteRead, status_code=201)
def add_note_route(
    request_id: int,
    payload: RequestNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestNote:
    return add_note(db, request_id=request_id, payload=payload, current_user=current_user)


@router.patch("/{request_id}/notes/{note_id}", response_model=RequestNoteRead)
def update_note_route(
    request_id: int,
    note_id: int,
    payload: RequestNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestNote:
    return update_note(
        db,
        request_id=request_id,
        note_id=note_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/{request_id}/proposed-cruises", response_model=ProposedCruiseRead, status_code=201)
def add_proposed_cruise_route(
    request_id: int,
    payload: ProposedCruiseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposedCruiseRead:
    return add_proposed_cruise(db, request_id=request_id, payload=payload, current_user=current_user)


@router.post(
    "/{request_id}/proposed-cruises/generate-from-research",
    response_model=GenerateProposedCruisesResponse,
)
def generate_proposed_cruises_from_research_document_route(
    request_id: int,
    payload: GenerateProposedCruisesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateProposedCruisesResponse:
    return generate_proposed_cruises_from_research_document(
        db,
        request_id=request_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{request_id}/proposed-cruises/bulk",
    response_model=BulkProposedCruiseCreateResponse,
    status_code=201,
)
def add_proposed_cruises_bulk_route(
    request_id: int,
    payload: BulkProposedCruiseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkProposedCruiseCreateResponse:
    return add_proposed_cruises_bulk(
        db,
        request_id=request_id,
        payload=payload,
        current_user=current_user,
    )


@router.patch(
    "/{request_id}/proposed-cruises/{cruise_id}",
    response_model=ProposedCruiseRead,
)
def update_proposed_cruise_route(
    request_id: int,
    cruise_id: int,
    payload: ProposedCruiseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProposedCruiseRead:
    return update_proposed_cruise(
        db,
        request_id=request_id,
        cruise_id=cruise_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/{request_id}/quoted-insurance", response_model=QuotedInsuranceRead, status_code=201)
def add_quoted_insurance_route(
    request_id: int,
    payload: QuotedInsuranceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotedInsurance:
    return add_quoted_insurance(db, request_id=request_id, payload=payload, current_user=current_user)


@router.patch(
    "/{request_id}/quoted-insurance/{quote_id}",
    response_model=QuotedInsuranceRead,
)
def update_quoted_insurance_route(
    request_id: int,
    quote_id: int,
    payload: QuotedInsuranceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotedInsurance:
    return update_quoted_insurance(
        db,
        request_id=request_id,
        quote_id=quote_id,
        payload=payload,
        current_user=current_user,
    )


@router.post(
    "/{request_id}/research-documents",
    response_model=ResearchDocumentRead,
    status_code=201,
)
async def upload_research_document_route(
    request_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestResearchDocument:
    return await upload_research_document(
        db,
        request_id=request_id,
        file=file,
        current_user=current_user,
    )


@router.get("/{request_id}/research-documents/{document_id}/content")
def get_research_document_content_route(
    request_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PlainTextResponse:
    return get_research_document_content(db, request_id, document_id)
