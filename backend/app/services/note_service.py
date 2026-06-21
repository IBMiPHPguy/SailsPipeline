from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload, noload

from app.models import RequestNote, RequestNoteAudit, User
from app.schemas import RequestNoteCreate, RequestNoteUpdate
from app.services.agency_service import (
    assert_child_belongs_to_request,
    get_travel_request_for_agency,
    require_record_for_agency,
)
from app.services.request_service import get_open_request, touch_request
from app.tenant_context import require_current_agency_id


def load_note(db: Session, note_id: int) -> RequestNote:
    return (
        db.query(RequestNote)
        .options(
            joinedload(RequestNote.created_by),
            joinedload(RequestNote.updated_by),
            joinedload(RequestNote.audits).joinedload(RequestNoteAudit.changed_by),
        )
        .filter(RequestNote.id == note_id)
        .one()
    )


def record_note_audit(
    db: Session,
    note: RequestNote,
    current_user: User,
    *,
    from_summary: str | None = None,
    to_summary: str | None = None,
    from_content: str | None = None,
    to_content: str | None = None,
) -> None:
    db.add(
        RequestNoteAudit(
            request_note_id=note.id,
            from_summary=from_summary,
            to_summary=to_summary,
            from_content=from_content,
            to_content=to_content,
            changed_by_id=current_user.id,
        )
    )


def list_request_notes(db: Session, request_id: int) -> list[RequestNote]:
    get_travel_request_for_agency(db, request_id, require_current_agency_id())
    return (
        db.query(RequestNote)
        .options(
            joinedload(RequestNote.created_by),
            joinedload(RequestNote.updated_by),
            noload(RequestNote.audits),
        )
        .filter(RequestNote.travel_request_id == request_id)
        .order_by(RequestNote.created_at.desc())
        .all()
    )


def get_request_note(db: Session, request_id: int, note_id: int) -> RequestNote:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    note = (
        db.query(RequestNote)
        .options(
            joinedload(RequestNote.created_by),
            joinedload(RequestNote.updated_by),
            joinedload(RequestNote.audits).joinedload(RequestNoteAudit.changed_by),
        )
        .filter(RequestNote.id == note_id, RequestNote.travel_request_id == request_id)
        .first()
    )
    require_record_for_agency(note, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=note.agency_id,
        child_travel_request_id=note.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )
    return note


def add_note(
    db: Session,
    *,
    request_id: int,
    payload: RequestNoteCreate,
    current_user: User,
) -> RequestNote:
    request = get_open_request(db, request_id)
    content = payload.content.strip()
    summary = payload.summary.strip()
    note = RequestNote(
        agency_id=request.agency_id,
        travel_request_id=request_id,
        summary=summary,
        content=content,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    touch_request(request, current_user)
    db.add(note)
    db.flush()
    record_note_audit(
        db,
        note,
        current_user,
        to_summary=summary,
        to_content=content,
    )
    db.commit()
    return load_note(db, note.id)


def update_note(
    db: Session,
    *,
    request_id: int,
    note_id: int,
    payload: RequestNoteUpdate,
    current_user: User,
) -> RequestNote:
    agency_id = require_current_agency_id()
    request = get_open_request(db, request_id)
    note = db.get(RequestNote, note_id)
    require_record_for_agency(note, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=note.agency_id,
        child_travel_request_id=note.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )

    updates = payload.model_dump(exclude_unset=True)
    changed = False
    summary_changed = False
    content_changed = False
    old_summary = note.summary
    old_content = note.content
    new_summary = old_summary
    new_content = old_content

    if "summary" in updates and updates["summary"] is not None:
        new_summary = updates["summary"].strip()
        summary_changed = new_summary != old_summary

    if "content" in updates and updates["content"] is not None:
        new_content = updates["content"].strip()
        content_changed = new_content != old_content

    if summary_changed or content_changed:
        record_note_audit(
            db,
            note,
            current_user,
            from_summary=old_summary if summary_changed else None,
            to_summary=new_summary if summary_changed else None,
            from_content=old_content if content_changed else None,
            to_content=new_content if content_changed else None,
        )
        if summary_changed:
            note.summary = new_summary
            changed = True
        if content_changed:
            note.content = new_content
            changed = True

    if changed:
        note.updated_by_id = current_user.id
        touch_request(request, current_user)

    db.commit()
    return load_note(db, note.id)
