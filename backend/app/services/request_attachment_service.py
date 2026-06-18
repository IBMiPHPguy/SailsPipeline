from fastapi import HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session, joinedload

from app.attachment_storage import read_attachment_text, store_upload_file
from app.config import settings
from app.constants import REQUEST_STATUS_CLOSED
from app.models import CallTranscript, ChatLog, RequestResearchDocument, TravelRequest, User
from app.services.request_service import get_open_request, touch_request


async def add_transcript(
    db: Session,
    *,
    request_id: int,
    file: UploadFile,
    current_user: User,
) -> CallTranscript:
    request = db.get(TravelRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Travel request not found.")
    if request.status == REQUEST_STATUS_CLOSED:
        raise HTTPException(status_code=400, detail="Closed requests cannot be updated.")

    stored_path, original_filename, mime_type, size_bytes = await store_upload_file(
        settings.attachments_dir,
        request_id,
        "transcripts",
        file,
    )
    transcript = CallTranscript(
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
    transcript = db.get(CallTranscript, transcript_id)
    if transcript is None or transcript.travel_request_id != request_id:
        raise HTTPException(status_code=404, detail="Call transcript not found.")

    content = read_attachment_text(
        settings.attachments_dir,
        transcript.stored_path,
        transcript.mime_type,
    )
    return PlainTextResponse(content)


async def add_chat_log(
    db: Session,
    *,
    request_id: int,
    file: UploadFile,
    current_user: User,
) -> ChatLog:
    request = db.get(TravelRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Travel request not found.")
    if request.status == REQUEST_STATUS_CLOSED:
        raise HTTPException(status_code=400, detail="Closed requests cannot be updated.")

    stored_path, original_filename, mime_type, size_bytes = await store_upload_file(
        settings.attachments_dir,
        request_id,
        "chats",
        file,
    )
    chat_log = ChatLog(
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
    chat_log = db.get(ChatLog, chat_id)
    if chat_log is None or chat_log.travel_request_id != request_id:
        raise HTTPException(status_code=404, detail="Chat log not found.")

    content = read_attachment_text(
        settings.attachments_dir,
        chat_log.stored_path,
        chat_log.mime_type,
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
        request_id,
        "research",
        file,
    )
    document = RequestResearchDocument(
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
    document = db.get(RequestResearchDocument, document_id)
    if document is None or document.travel_request_id != request_id:
        raise HTTPException(status_code=404, detail="Research document not found.")

    content = read_attachment_text(
        settings.attachments_dir,
        document.stored_path,
        document.mime_type,
    )
    return PlainTextResponse(content)
