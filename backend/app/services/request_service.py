from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit_helpers import (
    TRAVEL_REQUEST_AUDIT_FIELDS,
    apply_updates,
    collect_field_changes,
    record_travel_request_field_changes,
)
from app.constants import (
    ACTIVE_PIPELINE_QUOTE_STATUSES,
    PRIMARY_CLOSE_REASON,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    STALE_DAYS,
    TASK_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
)
from app.models import (
    CallTranscript,
    ChatLog,
    Passenger,
    ProposedCruise,
    ProposedCruisePassenger,
    QuotedInsurance,
    RequestCommunication,
    RequestNote,
    RequestPassenger,
    RequestPassengerAudit,
    RequestResearchDocument,
    RequestTaskLive,
    RequestWorkflowLive,
    TravelRequest,
    TravelRequestAudit,
    TravelRequestGroupBooking,
    User,
)
from app.services.workflow_read import resolve_workflow_name, workflow_to_read
from app.passenger_helpers import attach_passenger_to_request, create_passenger_record
from app.schemas import (
    AttachmentRead,
    DashboardNextOpenTaskRead,
    DashboardOpenRequest,
    QuotedInsuranceRead,
    RequestChangeHistoryRead,
    RequestCommunicationSummaryRead,
    RequestNoteSummaryRead,
    RequestPassengerAuditRead,
    RequestPassengerRead,
    ResearchDocumentRead,
    TravelRequestAuditRead,
    TravelRequestCreate,
    TravelRequestDetailRead,
    TravelRequestRead,
    TravelRequestUpdate,
    UserAudit,
)
from app.services.agency_service import get_travel_request_for_agency
from app.services.booked_cruise_metrics import calculate_open_pipeline_value as _calculate_open_pipeline_value
from app.services.passenger_service import sync_primary_passenger_from_request
from app.tenant_context import require_current_agency_id
from app.services.proposed_cruise_service import proposed_cruise_to_read
from app.workflow_helpers import (
    TASK_KEY_FOLLOW_UP_RESEARCH,
    ensure_follow_up_due_date,
)


def is_stale_by_last_worked(last_worked_at: datetime) -> bool:
    threshold = datetime.now(UTC) - timedelta(days=STALE_DAYS)
    if last_worked_at.tzinfo is None:
        return last_worked_at.replace(tzinfo=UTC) < threshold
    return last_worked_at < threshold


def resolve_last_worked(request: TravelRequest) -> tuple[datetime, User]:
    candidates: list[tuple[datetime, User]] = [
        (request.updated_at, request.updated_by),
    ]
    for workflow in request.request_workflows_live:
        candidates.append((workflow.started_at, workflow.started_by))
        if workflow.ended_at is not None and workflow.completed_by is not None:
            candidates.append((workflow.ended_at, workflow.completed_by))
        for task in workflow.tasks:
            if task.completed_at is not None and task.completed_by is not None:
                candidates.append((task.completed_at, task.completed_by))
    return max(candidates, key=lambda item: item[0])


def resolve_next_open_task(request: TravelRequest) -> DashboardNextOpenTaskRead | None:
    active_workflow = next(
        (workflow for workflow in request.request_workflows_live if workflow.status == WORKFLOW_STATUS_ACTIVE),
        None,
    )
    if active_workflow is None:
        return None

    open_tasks = sorted(
        (task for task in active_workflow.tasks if task.status == TASK_STATUS_OPEN),
        key=lambda task: task.sequence_order,
    )
    if not open_tasks:
        return None

    task = open_tasks[0]
    workflow_type = active_workflow.workflow_type_key or active_workflow.workflow_name
    return DashboardNextOpenTaskRead(
        id=task.id,
        task_key=task.task_key or "",
        title=task.task_title,
        workflow_type=workflow_type,
        workflow_name=resolve_workflow_name(active_workflow),
    )


def build_dashboard_open_request(request: TravelRequest) -> DashboardOpenRequest:
    last_worked_at, last_worked_by = resolve_last_worked(request)
    base = TravelRequestRead.model_validate(request)
    return DashboardOpenRequest(
        **base.model_dump(),
        is_stale=is_stale_by_last_worked(last_worked_at),
        next_open_task=resolve_next_open_task(request),
        last_worked_at=last_worked_at,
        last_worked_by=UserAudit.model_validate(last_worked_by),
    )


def count_stale_open_requests(db: Session, agency_id: str) -> int:
    open_requests = (
        dashboard_query(db)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequest.status == REQUEST_STATUS_OPEN,
        )
        .all()
    )
    return sum(
        1
        for request in open_requests
        if is_stale_by_last_worked(resolve_last_worked(request)[0])
    )


def dashboard_query(db: Session):
    return db.query(TravelRequest).options(
        joinedload(TravelRequest.created_by),
        joinedload(TravelRequest.updated_by),
        joinedload(TravelRequest.request_workflows_live).options(
            joinedload(RequestWorkflowLive.started_by),
            joinedload(RequestWorkflowLive.completed_by),
            joinedload(RequestWorkflowLive.tasks).joinedload(RequestTaskLive.completed_by),
        ),
    )


def request_query(db: Session):
    return db.query(TravelRequest).options(
        joinedload(TravelRequest.created_by),
        joinedload(TravelRequest.updated_by),
    )


def detail_query(db: Session):
    return db.query(TravelRequest).options(
        joinedload(TravelRequest.created_by),
        joinedload(TravelRequest.updated_by),
        selectinload(TravelRequest.request_passengers).joinedload(RequestPassenger.passenger),
        selectinload(TravelRequest.request_notes).options(
            joinedload(RequestNote.created_by),
            joinedload(RequestNote.updated_by),
        ),
        selectinload(TravelRequest.proposed_cruises).options(
            joinedload(ProposedCruise.created_by),
            joinedload(ProposedCruise.updated_by),
            selectinload(ProposedCruise.passenger_links)
            .joinedload(ProposedCruisePassenger.request_passenger)
            .joinedload(RequestPassenger.passenger),
        ),
        selectinload(TravelRequest.quoted_insurance).options(
            joinedload(QuotedInsurance.created_by),
            joinedload(QuotedInsurance.updated_by),
        ),
        selectinload(TravelRequest.call_transcripts).joinedload(CallTranscript.created_by),
        selectinload(TravelRequest.chat_logs).joinedload(ChatLog.created_by),
        selectinload(TravelRequest.request_workflows_live).options(
            joinedload(RequestWorkflowLive.started_by),
            joinedload(RequestWorkflowLive.completed_by),
            selectinload(RequestWorkflowLive.tasks).joinedload(RequestTaskLive.completed_by),
        ),
        selectinload(TravelRequest.request_communications).options(
            joinedload(RequestCommunication.created_by),
            joinedload(RequestCommunication.updated_by),
        ),
        selectinload(TravelRequest.research_documents).joinedload(RequestResearchDocument.uploaded_by),
        joinedload(TravelRequest.agency_group),
        joinedload(TravelRequest.group_inventory),
        selectinload(TravelRequest.group_bookings).joinedload(TravelRequestGroupBooking.group_inventory),
    )


def load_change_history(db: Session, request_id: int) -> TravelRequest | None:
    return (
        db.query(TravelRequest)
        .options(
            selectinload(TravelRequest.request_audits).joinedload(TravelRequestAudit.changed_by),
            selectinload(TravelRequest.passenger_audits).joinedload(RequestPassengerAudit.changed_by),
        )
        .filter(TravelRequest.id == request_id)
        .first()
    )


def get_open_request(db: Session, request_id: int) -> TravelRequest:
    request = get_travel_request_for_agency(db, request_id, require_current_agency_id())
    if request.status == REQUEST_STATUS_CLOSED:
        raise HTTPException(status_code=400, detail="Closed requests cannot be updated.")
    return request


def touch_request(request: TravelRequest, current_user: User) -> None:
    request.updated_by_id = current_user.id
    request.updated_at = datetime.now(UTC).replace(tzinfo=None)


def request_detail_to_read(request: TravelRequest) -> TravelRequestDetailRead:
    from app.services.agency_group_service import group_booking_read_payload, group_intake_summary_payload

    last_worked_at, last_worked_by = resolve_last_worked(request)
    base = TravelRequestRead.model_validate(request)
    group_summary = (
        group_intake_summary_payload(request.agency_group) if request.agency_group is not None else None
    )
    group_bookings = [
        group_booking_read_payload(booking) for booking in request.group_bookings
    ]
    return TravelRequestDetailRead(
        **base.model_dump(),
        last_worked_at=last_worked_at,
        last_worked_by=UserAudit.model_validate(last_worked_by),
        group_summary=group_summary,
        group_bookings=group_bookings,
        request_passengers=[RequestPassengerRead.model_validate(passenger) for passenger in request.request_passengers],
        request_notes=[RequestNoteSummaryRead.model_validate(note) for note in request.request_notes],
        call_transcripts=[AttachmentRead.model_validate(attachment) for attachment in request.call_transcripts],
        chat_logs=[AttachmentRead.model_validate(attachment) for attachment in request.chat_logs],
        proposed_cruises=[
            proposed_cruise_to_read(cruise, request.cabins_needed) for cruise in request.proposed_cruises
        ],
        quoted_insurance=[QuotedInsuranceRead.model_validate(quote) for quote in request.quoted_insurance],
        request_workflows=[workflow_to_read(workflow) for workflow in request.request_workflows_live],
        request_communications=[
            RequestCommunicationSummaryRead.model_validate(communication)
            for communication in request.request_communications
        ],
        research_documents=[
            ResearchDocumentRead.model_validate(document) for document in request.research_documents
        ],
    )


def sync_communicate_research_follow_up_due_dates(db: Session, request: TravelRequest) -> None:
    changed = False
    for workflow in request.request_workflows_live:
        if workflow.status != WORKFLOW_STATUS_ACTIVE:
            continue
        follow_up = next(
            (task for task in workflow.tasks if task.task_key == TASK_KEY_FOLLOW_UP_RESEARCH),
            None,
        )
        previous_due_at = follow_up.due_at if follow_up is not None else None
        ensure_follow_up_due_date(workflow)
        if follow_up is not None and follow_up.due_at != previous_due_at:
            changed = True
    if changed:
        db.commit()


def list_requests(db: Session) -> list[TravelRequest]:
    return request_query(db).order_by(TravelRequest.created_at.desc()).all()


CLOSED_REQUESTS_PAGE_SIZE_DEFAULT = 25
CLOSED_REQUESTS_PAGE_SIZE_MAX = 100


def search_closed_requests(
    db: Session,
    *,
    query: str = "",
    page: int = 1,
    page_size: int = CLOSED_REQUESTS_PAGE_SIZE_DEFAULT,
) -> tuple[list[TravelRequest], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, CLOSED_REQUESTS_PAGE_SIZE_MAX))

    base = request_query(db).filter(TravelRequest.status == REQUEST_STATUS_CLOSED)
    term = query.strip()
    if term:
        pattern = f"%{term}%"
        phone_digits = "".join(character for character in term if character.isdigit())
        filters = [
            TravelRequest.first_name.ilike(pattern),
            TravelRequest.last_name.ilike(pattern),
            TravelRequest.email.ilike(pattern),
            TravelRequest.phone.ilike(pattern),
            TravelRequest.destination.ilike(pattern),
            TravelRequest.close_reason.ilike(pattern),
            func.concat(TravelRequest.first_name, " ", TravelRequest.last_name).ilike(pattern),
            cast(TravelRequest.cruise_lines, String).ilike(pattern),
            User.username.ilike(pattern),
        ]
        if phone_digits:
            filters.append(TravelRequest.phone.ilike(f"%{phone_digits}%"))
        base = base.join(TravelRequest.updated_by).filter(or_(*filters))

    total = base.count()
    items = (
        base.order_by(TravelRequest.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def closed_requests_total_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return ceil(total / page_size)


def calculate_open_pipeline_value(db: Session) -> float:
    """Sum booked cruise costs on open requests; otherwise the highest active quote per request."""
    return _calculate_open_pipeline_value(db)


def search_open_requests(
    db: Session,
    *,
    query: str = "",
    page: int = 1,
    page_size: int = CLOSED_REQUESTS_PAGE_SIZE_DEFAULT,
) -> tuple[list[DashboardOpenRequest], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, CLOSED_REQUESTS_PAGE_SIZE_MAX))

    base = dashboard_query(db).filter(TravelRequest.status == REQUEST_STATUS_OPEN)
    term = query.strip()
    if term:
        pattern = f"%{term}%"
        phone_digits = "".join(character for character in term if character.isdigit())
        filters = [
            TravelRequest.first_name.ilike(pattern),
            TravelRequest.last_name.ilike(pattern),
            TravelRequest.email.ilike(pattern),
            TravelRequest.phone.ilike(pattern),
            TravelRequest.destination.ilike(pattern),
            func.concat(TravelRequest.first_name, " ", TravelRequest.last_name).ilike(pattern),
            cast(TravelRequest.cruise_lines, String).ilike(pattern),
            User.username.ilike(pattern),
            RequestTaskLive.task_title.ilike(pattern),
            RequestTaskLive.task_key.ilike(pattern),
            RequestWorkflowLive.workflow_name.ilike(pattern),
        ]
        if phone_digits:
            filters.append(TravelRequest.phone.ilike(f"%{phone_digits}%"))
        base = (
            base.outerjoin(TravelRequest.updated_by)
            .outerjoin(TravelRequest.request_workflows_live)
            .outerjoin(RequestWorkflowLive.tasks)
            .filter(or_(*filters))
            .distinct()
        )

    requests = base.all()
    items = [build_dashboard_open_request(request) for request in requests]
    items.sort(key=lambda item: item.last_worked_at)
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def reopen_request(db: Session, request_id: int, current_user: User) -> TravelRequest:
    request = get_travel_request_for_agency(db, request_id, require_current_agency_id())
    if request.status != REQUEST_STATUS_CLOSED:
        raise HTTPException(status_code=400, detail="Only closed requests can be reopened.")
    if request.close_reason == PRIMARY_CLOSE_REASON:
        raise HTTPException(
            status_code=400,
            detail="Requests closed as purchased trips cannot be reopened.",
        )

    updates = {
        "status": REQUEST_STATUS_OPEN,
        "close_reason": None,
    }
    request_changes = collect_field_changes(request, updates, TRAVEL_REQUEST_AUDIT_FIELDS)
    record_travel_request_field_changes(db, request, request_changes, current_user)
    apply_updates(request, updates)
    touch_request(request, current_user)
    db.commit()
    from app.services.agency_rollup_service import schedule_agency_rollup_refresh

    schedule_agency_rollup_refresh(current_user.agency_id)
    return request_query(db).filter(TravelRequest.id == request_id).one()


def create_request(db: Session, payload: TravelRequestCreate, current_user: User) -> TravelRequest:
    if payload.return_date <= payload.departure_date:
        raise HTTPException(status_code=400, detail="Return date must be after departure date.")

    data = payload.model_dump(
        exclude={"first_passenger_date_of_birth", "primary_passenger_id", "group_bookings"},
    )
    request_qualifiers = data.pop("qualifiers", []) or []
    if payload.destination_details:
        data["destination_details"] = payload.destination_details.model_dump(exclude_none=True)
    else:
        data["destination_details"] = None

    if payload.primary_passenger_id is not None:
        passenger = db.get(Passenger, payload.primary_passenger_id)
        if passenger is None:
            raise HTTPException(status_code=404, detail="Passenger not found.")
        if passenger.agency_id != current_user.agency_id:
            raise HTTPException(status_code=404, detail="Passenger not found.")
        if not passenger.is_active:
            raise HTTPException(status_code=400, detail="Inactive clients cannot be used for new requests.")
        data["first_name"] = passenger.first_name
        data["last_name"] = passenger.last_name
        data["email"] = passenger.email
        data["phone"] = passenger.phone
        if payload.first_passenger_date_of_birth is not None:
            passenger.date_of_birth = payload.first_passenger_date_of_birth

    if payload.marketing_campaign_id is not None:
        from app.services.agency_service import get_marketing_campaign_for_agency

        get_marketing_campaign_for_agency(db, payload.marketing_campaign_id, current_user.agency_id)

    from app.services.agency_group_service import (
        normalize_group_booking_inputs,
        replace_travel_request_group_bookings,
        validate_travel_request_group_alignment,
        validate_travel_request_group_linkage,
    )

    group_booking_rows: list[dict] = []
    if payload.group_id:
        validate_travel_request_group_linkage(
            db,
            agency_id=current_user.agency_id,
            group_id=payload.group_id,
            group_inventory_id=payload.group_inventory_id,
        )
        validate_travel_request_group_alignment(
            db,
            agency_id=current_user.agency_id,
            group_id=payload.group_id,
            cruise_lines=payload.cruise_lines,
            ship_name=payload.ship_name,
            departure_date=payload.departure_date,
            return_date=payload.return_date,
        )
        group_booking_rows, cabin_types, total_cabins = normalize_group_booking_inputs(
            db,
            agency_id=current_user.agency_id,
            group_id=payload.group_id,
            bookings=[row.model_dump() for row in payload.group_bookings],
            fallback_inventory_id=payload.group_inventory_id,
            fallback_cabins_requested=payload.cabins_needed,
        )
        if group_booking_rows:
            data["group_inventory_id"] = group_booking_rows[0]["group_inventory_id"]
            data["cabin_types"] = list(dict.fromkeys(cabin_types))
            data["cabins_needed"] = total_cabins
    elif payload.group_bookings or payload.group_inventory_id:
        raise HTTPException(
            status_code=400,
            detail="group_id is required when group inventory bookings are provided.",
        )
    else:
        validate_travel_request_group_linkage(
            db,
            agency_id=current_user.agency_id,
            group_id=payload.group_id,
            group_inventory_id=payload.group_inventory_id,
        )

    request = TravelRequest(
        **data,
        agency_id=current_user.agency_id,
        status=REQUEST_STATUS_OPEN,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(request)
    db.flush()

    if payload.primary_passenger_id is not None:
        attach_passenger_to_request(
            db,
            request.id,
            payload.primary_passenger_id,
            is_primary=True,
            qualifiers=request_qualifiers,
        )
    else:
        passenger = create_passenger_record(
            db,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            date_of_birth=payload.first_passenger_date_of_birth,
            created_by_id=current_user.id,
        )
        attach_passenger_to_request(
            db,
            request.id,
            passenger.id,
            is_primary=True,
            qualifiers=request_qualifiers,
        )

    if group_booking_rows:
        replace_travel_request_group_bookings(
            db,
            request=request,
            booking_rows=group_booking_rows,
        )
        from app.services.agency_group_service import get_agency_group_detail
        from app.services.group_intake_proposed_cruise_service import seed_proposed_cruise_from_group_intake

        group = get_agency_group_detail(
            db,
            agency_id=current_user.agency_id,
            group_id=payload.group_id,
        )
        seed_proposed_cruise_from_group_intake(
            db,
            request=request,
            group=group,
            group_booking_rows=group_booking_rows,
            current_user=current_user,
        )

    db.commit()
    from app.services.agency_rollup_service import schedule_agency_rollup_refresh

    schedule_agency_rollup_refresh(current_user.agency_id)
    return request_query(db).filter(TravelRequest.id == request.id).one()


def get_request_detail(db: Session, request_id: int) -> TravelRequestDetailRead:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    request = detail_query(db).filter(TravelRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Travel request not found.")
    sync_communicate_research_follow_up_due_dates(db, request)
    return request_detail_to_read(request)


def get_request_change_history(db: Session, request_id: int) -> RequestChangeHistoryRead:
    get_travel_request_for_agency(db, request_id, require_current_agency_id())
    request = load_change_history(db, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Travel request not found.")
    return RequestChangeHistoryRead(
        request_audits=[TravelRequestAuditRead.model_validate(audit) for audit in request.request_audits],
        passenger_audits=[
            RequestPassengerAuditRead.model_validate(audit) for audit in request.passenger_audits
        ],
    )


def update_request(
    db: Session,
    *,
    request_id: int,
    payload: TravelRequestUpdate,
    current_user: User,
) -> TravelRequestDetailRead:
    request = get_open_request(db, request_id)
    updates = payload.model_dump(exclude_unset=True)
    departure = updates.get("departure_date", request.departure_date)
    returning = updates.get("return_date", request.return_date)
    if returning <= departure:
        raise HTTPException(status_code=400, detail="Return date must be after departure date.")

    next_status = updates.get("status", request.status)
    next_close_reason = updates.get("close_reason", request.close_reason)
    from app.services.group_inventory_reservation_service import (
        maybe_apply_group_inventory_reservation_on_purchase,
    )

    maybe_apply_group_inventory_reservation_on_purchase(
        db,
        request_id=request_id,
        agency_id=current_user.agency_id,
        next_status=next_status,
        next_close_reason=next_close_reason,
    )

    request_changes = collect_field_changes(request, updates, TRAVEL_REQUEST_AUDIT_FIELDS)
    record_travel_request_field_changes(db, request, request_changes, current_user)
    apply_updates(request, updates)

    if "marketing_campaign_id" in updates and updates["marketing_campaign_id"] is not None:
        from app.services.agency_service import get_marketing_campaign_for_agency

        get_marketing_campaign_for_agency(db, updates["marketing_campaign_id"], current_user.agency_id)

    if "group_id" in updates and updates.get("group_id") is None:
        updates["group_inventory_id"] = None

    if "group_id" in updates or "group_inventory_id" in updates:
        from app.services.agency_group_service import validate_travel_request_group_linkage

        next_group_id = updates.get("group_id", request.group_id)
        next_inventory_id = updates.get("group_inventory_id", request.group_inventory_id)
        validate_travel_request_group_linkage(
            db,
            agency_id=current_user.agency_id,
            group_id=next_group_id,
            group_inventory_id=next_inventory_id,
        )

    sync_primary_passenger_from_request(request, db, current_user)
    touch_request(request, current_user)
    db.commit()
    from app.services.agency_rollup_service import schedule_agency_rollup_refresh

    schedule_agency_rollup_refresh(current_user.agency_id)
    request = detail_query(db).filter(TravelRequest.id == request_id).one()
    return request_detail_to_read(request)
