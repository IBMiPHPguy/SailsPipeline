from fastapi import HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.attachment_storage import read_attachment_text, store_upload_file
from app.config import settings
from app.constants import REQUEST_STATUS_CLOSED
from app.models import CallTranscript, ChatLog, RequestResearchDocument, User
from app.services.agency_service import (
    assert_child_belongs_to_request,
    get_travel_request_for_agency,
    require_record_for_agency,
)
from app.services.request_service import get_open_request, touch_request
from app.tenant_context import require_current_agency_id


async def add_transcript(
    db: Session,
    *,
    request_id: int,
    file: UploadFile,
    current_user: User,
) -> CallTranscript:
    request = get_open_request(db, request_id)
    stored_path, original_filename, mime_type, size_bytes = await store_upload_file(
        settings.attachments_dir,
        request.agency_id,
        request_id,
        "transcripts",
        file,
    )
    transcript = CallTranscript(
        agency_id=request.agency_id,
        travel_request_id=request_id,
        original_filename=original_filename,
        stored_path=stored_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        created_by_id=current_user.id,
    )
    touch_request(request, current_user)
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return (
        db.query(CallTranscript)
        .options(joinedload(CallTranscript.created_by))
        .filter(CallTranscript.id == transcript.id)
        .one()
    )


def get_transcript_content(db: Session, request_id: int, transcript_id: int) -> PlainTextResponse:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    transcript = db.get(CallTranscript, transcript_id)
    require_record_for_agency(transcript, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=transcript.agency_id,
        child_travel_request_id=transcript.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )

    content = read_attachment_text(
        settings.attachments_dir,
        transcript.stored_path,
        transcript.mime_type,
        agency_id=agency_id,
    )
    return PlainTextResponse(content)


async def add_chat_log(
    db: Session,
    *,
    request_id: int,
    file: UploadFile,
    current_user: User,
) -> ChatLog:
    request = get_open_request(db, request_id)
    stored_path, original_filename, mime_type, size_bytes = await store_upload_file(
        settings.attachments_dir,
        request.agency_id,
        request_id,
        "chats",
        file,
    )
    chat_log = ChatLog(
        agency_id=request.agency_id,
        travel_request_id=request_id,
        original_filename=original_filename,
        stored_path=stored_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        created_by_id=current_user.id,
    )
    touch_request(request, current_user)
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)
    return (
        db.query(ChatLog)
        .options(joinedload(ChatLog.created_by))
        .filter(ChatLog.id == chat_log.id)
        .one()
    )


def get_chat_log_content(db: Session, request_id: int, chat_id: int) -> PlainTextResponse:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    chat_log = db.get(ChatLog, chat_id)
    require_record_for_agency(chat_log, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=chat_log.agency_id,
        child_travel_request_id=chat_log.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )

    content = read_attachment_text(
        settings.attachments_dir,
        chat_log.stored_path,
        chat_log.mime_type,
        agency_id=agency_id,
    )
    return PlainTextResponse(content)


async def upload_research_document(
    db: Session,
    *,
    request_id: int,
    file: UploadFile,
    current_user: User,
) -> RequestResearchDocument:
    request = get_open_request(db, request_id)
    filename = (file.filename or "").lower()
    if not filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Research documents must be .txt files.")

    stored_path, original_filename, mime_type, size_bytes = await store_upload_file(
        settings.attachments_dir,
        request.agency_id,
        request_id,
        "research",
        file,
    )
    document = RequestResearchDocument(
        agency_id=request.agency_id,
        travel_request_id=request_id,
        original_filename=original_filename,
        stored_path=stored_path,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_by_id=current_user.id,
    )
    touch_request(request, current_user)
    db.add(document)
    db.commit()
    db.refresh(document)
    return (
        db.query(RequestResearchDocument)
        .options(joinedload(RequestResearchDocument.uploaded_by))
        .filter(RequestResearchDocument.id == document.id)
        .one()
    )


def get_research_document_content(db: Session, request_id: int, document_id: int) -> PlainTextResponse:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    document = db.get(RequestResearchDocument, document_id)
    require_record_for_agency(document, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=document.agency_id,
        child_travel_request_id=document.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )

    content = read_attachment_text(
        settings.attachments_dir,
        document.stored_path,
        document.mime_type,
        agency_id=agency_id,
    )
    return PlainTextResponse(content)
