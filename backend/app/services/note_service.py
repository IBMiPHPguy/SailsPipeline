from sqlalchemy.orm import Session, joinedload, noload

from app.models import RequestNote, RequestNoteAudit, TravelRequest, User
from app.schemas import RequestNoteCreate, RequestNoteUpdate
from app.services.request_service import get_open_request, touch_request


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
    request = db.get(TravelRequest, request_id)
    if request is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Travel request not found.")
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
    from fastapi import HTTPException

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
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
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
    from fastapi import HTTPException

    request = get_open_request(db, request_id)
    note = db.get(RequestNote, note_id)
    if note is None or note.travel_request_id != request_id:
        raise HTTPException(status_code=404, detail="Note not found.")

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
