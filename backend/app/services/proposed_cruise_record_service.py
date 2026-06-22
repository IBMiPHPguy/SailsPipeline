from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.constants import (
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
)
from app.gemini_service import (
    GeminiConfigurationError,
    GeminiParseError,
    generate_proposed_cruises_from_research,
)
from app.models import (
    ProposedCruise,
    ProposedCruisePassenger,
    RequestPassenger,
    RequestResearchDocument,
    TravelRequest,
    User,
)
from app.proposed_cruise_helpers import (
    default_proposed_cruise_includes_dict,
    flatten_room_passenger_ids,
    normalize_cabin_pricing_list,
    normalize_cabin_rooms_list,
    normalize_room_passenger_ids,
    passengers_in_room_limits_for_cruise,
    sync_cruise_from_cabin_rooms,
    sync_cruise_totals_from_cabin_pricing,
    validate_proposed_cruise_rejection,
)
from app.schemas import (
    BulkProposedCruiseCreate,
    BulkProposedCruiseCreateResponse,
    GenerateProposedCruisesRequest,
    GenerateProposedCruisesResponse,
    ProposedCruiseCreate,
    ProposedCruiseRead,
    ProposedCruiseUpdate,
)
from app.services.agency_service import assert_child_belongs_to_request, require_record_for_agency
from app.services.gemini_context_service import build_request_context_for_gemini
from app.services.proposed_cruise_service import proposed_cruise_to_read
from app.services.agency_rollup_service import (
    rollup_refresh_triggers_on_cruise_status,
    schedule_agency_rollup_refresh,
)
from app.services.request_service import get_open_request, touch_request
from app.tenant_context import require_current_agency_id
from app.attachment_storage import read_attachment_text


def load_proposed_cruise(db: Session, cruise_id: int) -> ProposedCruise:
    return (
        db.query(ProposedCruise)
        .options(
            joinedload(ProposedCruise.created_by),
            joinedload(ProposedCruise.updated_by),
            joinedload(ProposedCruise.passenger_links).joinedload(ProposedCruisePassenger.request_passenger).joinedload(
                RequestPassenger.passenger
            ),
        )
        .filter(ProposedCruise.id == cruise_id)
        .one()
    )


def validate_proposed_cruise_passengers(
    db: Session,
    request_id: int,
    passenger_ids: list[int],
) -> None:
    if not passenger_ids:
        return
    valid_ids = {
        passenger.id
        for passenger in db.query(RequestPassenger)
        .filter(RequestPassenger.travel_request_id == request_id)
        .all()
    }
    invalid = [passenger_id for passenger_id in passenger_ids if passenger_id not in valid_ids]
    if invalid:
        raise HTTPException(status_code=400, detail="One or more selected passengers are invalid.")


def validate_proposed_cruise_room_passengers(
    db: Session,
    request_id: int,
    room_passenger_ids: list[list[int]],
    passengers_in_room_limits: list[int],
) -> None:
    flat_passenger_ids = flatten_room_passenger_ids(room_passenger_ids)
    validate_proposed_cruise_passengers(db, request_id, flat_passenger_ids)

    if len(flat_passenger_ids) != len(set(flat_passenger_ids)):
        raise HTTPException(status_code=400, detail="Each passenger can only be assigned to one room.")

    for cabin_index, room in enumerate(room_passenger_ids):
        limit = (
            passengers_in_room_limits[cabin_index]
            if cabin_index < len(passengers_in_room_limits)
            else passengers_in_room_limits[-1]
        )
        if len(room) > limit:
            raise HTTPException(
                status_code=400,
                detail=f"Room {cabin_index + 1} exceeds the passengers-in-room limit.",
            )


def sync_proposed_cruise_room_passengers(
    db: Session,
    cruise: ProposedCruise,
    room_passenger_ids: list[list[int]],
    request_id: int,
    cabins_needed: int = 1,
) -> None:
    validate_proposed_cruise_room_passengers(
        db,
        request_id,
        room_passenger_ids,
        passengers_in_room_limits_for_cruise(cruise, cabins_needed),
    )
    cruise.passenger_links.clear()
    for cabin_index, passenger_ids in enumerate(room_passenger_ids):
        for passenger_id in passenger_ids:
            cruise.passenger_links.append(
                ProposedCruisePassenger(
                    request_passenger_id=passenger_id,
                    cabin_index=cabin_index,
                )
            )


def assign_default_passenger_ids(db: Session, request_id: int, passengers_in_room: int) -> list[int]:
    links = (
        db.query(RequestPassenger)
        .filter(RequestPassenger.travel_request_id == request_id)
        .order_by(RequestPassenger.is_primary.desc(), RequestPassenger.id.asc())
        .all()
    )
    if not links:
        return []
    count = min(max(passengers_in_room, 1), len(links))
    return [link.id for link in links[:count]]


def assign_default_room_passenger_ids(
    db: Session,
    request_id: int,
    passengers_in_room: int,
    cabins_needed: int,
) -> list[list[int]]:
    passenger_ids = assign_default_passenger_ids(db, request_id, passengers_in_room)
    return normalize_room_passenger_ids(None, passenger_ids, cabins_needed)


def create_proposed_cruise_record(
    db: Session,
    request: TravelRequest,
    payload: ProposedCruiseCreate,
    current_user: User,
) -> ProposedCruise:
    validate_proposed_cruise_passengers(
        db,
        request.id,
        flatten_room_passenger_ids(
            normalize_room_passenger_ids(
                payload.room_passenger_ids,
                payload.passenger_ids,
                request.cabins_needed,
            )
        ),
    )
    data = payload.model_dump(exclude={"passenger_ids", "room_passenger_ids", "includes", "cabin_rooms", "cabin_pricing"})
    cruise = ProposedCruise(
        agency_id=request.agency_id,
        travel_request_id=request.id,
        **data,
        includes=payload.includes.model_dump(),
        status=PROPOSED_CRUISE_STATUS_PROPOSED,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    cabin_rooms = normalize_cabin_rooms_list(
        [room.model_dump() for room in payload.cabin_rooms] if payload.cabin_rooms else None,
        request.cabins_needed,
        room_category=payload.room_category,
        room_number=payload.room_number,
        passengers_in_room=payload.passengers_in_room,
        deposit_amount=Decimal(str(payload.deposit_amount)),
        cost=Decimal(str(payload.cost)),
        includes=payload.includes,
        cabin_pricing=None,
    )
    sync_cruise_from_cabin_rooms(cruise, cabin_rooms)
    db.add(cruise)
    db.flush()
    room_passenger_ids = normalize_room_passenger_ids(
        payload.room_passenger_ids,
        payload.passenger_ids,
        request.cabins_needed,
    )
    sync_proposed_cruise_room_passengers(db, cruise, room_passenger_ids, request.id, request.cabins_needed)
    return cruise


def add_proposed_cruise(
    db: Session,
    *,
    request_id: int,
    payload: ProposedCruiseCreate,
    current_user: User,
) -> ProposedCruiseRead:
    request = get_open_request(db, request_id)
    cruise = create_proposed_cruise_record(db, request, payload, current_user)
    touch_request(request, current_user)
    db.commit()
    return proposed_cruise_to_read(load_proposed_cruise(db, cruise.id), request.cabins_needed)


def generate_proposed_cruises_from_research_document(
    db: Session,
    *,
    request_id: int,
    payload: GenerateProposedCruisesRequest,
    current_user: User,
) -> GenerateProposedCruisesResponse:
    request = get_open_request(db, request_id)
    document = db.get(RequestResearchDocument, payload.research_document_id)
    require_record_for_agency(document, agency_id=request.agency_id)
    assert_child_belongs_to_request(
        child_agency_id=document.agency_id,
        child_travel_request_id=document.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    research_text = read_attachment_text(
        settings.attachments_dir,
        document.stored_path,
        document.mime_type,
        agency_id=request.agency_id,
    )
    request_context = build_request_context_for_gemini(request)

    try:
        cruises, model_name = generate_proposed_cruises_from_research(
            api_key=settings.gemini_api_key or "",
            model_name=settings.gemini_model,
            research_text=research_text,
            request_context=request_context,
        )
    except GeminiConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="Gemini is not configured. Add GEMINI_API_KEY to your environment.",
        ) from exc
    except GeminiParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    enriched: list[ProposedCruiseCreate] = []
    for cruise in cruises:
        room_passenger_ids = assign_default_room_passenger_ids(
            db,
            request_id,
            cruise.passengers_in_room,
            request.cabins_needed,
        )
        enriched.append(cruise.model_copy(update={"room_passenger_ids": room_passenger_ids, "passenger_ids": []}))

    return GenerateProposedCruisesResponse(
        research_document_id=document.id,
        research_document_filename=document.original_filename,
        model=model_name,
        cruises=enriched,
    )


def add_proposed_cruises_bulk(
    db: Session,
    *,
    request_id: int,
    payload: BulkProposedCruiseCreate,
    current_user: User,
) -> BulkProposedCruiseCreateResponse:
    request = get_open_request(db, request_id)
    created_ids: list[int] = []
    for cruise_payload in payload.cruises:
        cruise = create_proposed_cruise_record(db, request, cruise_payload, current_user)
        created_ids.append(cruise.id)
    touch_request(request, current_user)
    db.commit()
    created = [
        proposed_cruise_to_read(load_proposed_cruise(db, cruise_id), request.cabins_needed)
        for cruise_id in created_ids
    ]
    return BulkProposedCruiseCreateResponse(cruises=created)


def update_proposed_cruise(
    db: Session,
    *,
    request_id: int,
    cruise_id: int,
    payload: ProposedCruiseUpdate,
    current_user: User,
) -> ProposedCruiseRead:
    request = get_open_request(db, request_id)
    cruise = db.get(ProposedCruise, cruise_id)
    require_record_for_agency(cruise, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=cruise.agency_id,
        child_travel_request_id=cruise.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

    updates = payload.model_dump(exclude_unset=True)
    room_passenger_ids = updates.pop("room_passenger_ids", None)
    passenger_ids = updates.pop("passenger_ids", None)
    includes = updates.pop("includes", None)
    cabin_pricing = updates.pop("cabin_pricing", None)
    cabin_rooms = updates.pop("cabin_rooms", None)
    cabin_hold_reservation_ids = updates.pop("cabin_hold_reservation_ids", None)
    rejection_reason = updates.pop("rejection_reason", None)
    rejection_reason_detail = updates.pop("rejection_reason_detail", None)

    next_status = updates.get("status", cruise.status)
    rejection_fields_provided = (
        "rejection_reason" in payload.model_fields_set
        or "rejection_reason_detail" in payload.model_fields_set
    )
    require_rejection_reason = (
        next_status == PROPOSED_CRUISE_STATUS_REJECTED and rejection_fields_provided
    )
    validated_reason, validated_detail = validate_proposed_cruise_rejection(
        status=next_status,
        rejection_reason=rejection_reason,
        rejection_reason_detail=rejection_reason_detail,
        require_reason=require_rejection_reason,
    )

    if includes is not None:
        cruise.includes = includes.model_dump() if hasattr(includes, "model_dump") else includes

    for field, value in updates.items():
        setattr(cruise, field, value)

    if next_status == PROPOSED_CRUISE_STATUS_REJECTED:
        if rejection_fields_provided:
            cruise.rejection_reason = validated_reason
            cruise.rejection_reason_detail = validated_detail
    elif "status" in updates:
        cruise.rejection_reason = None
        cruise.rejection_reason_detail = None

    if cabin_rooms is not None:
        normalized_rooms = normalize_cabin_rooms_list(
            [room.model_dump() if hasattr(room, "model_dump") else room for room in cabin_rooms],
            request.cabins_needed,
            room_category=cruise.room_category,
            room_number=cruise.room_number,
            passengers_in_room=cruise.passengers_in_room,
            deposit_amount=Decimal(str(cruise.deposit_amount)),
            cost=Decimal(str(cruise.cost)),
            includes=cruise.includes or default_proposed_cruise_includes_dict(),
            cabin_pricing=cruise.cabin_pricing,
        )
        sync_cruise_from_cabin_rooms(cruise, normalized_rooms)
    elif cabin_pricing is not None or (
        updates.get("status", cruise.status) in {PROPOSED_CRUISE_STATUS_ACCEPTED, PROPOSED_CRUISE_STATUS_DEPOSITED}
        and not cruise.cabin_pricing
    ):
        normalized = normalize_cabin_pricing_list(
            cabin_pricing if cabin_pricing is not None else cruise.cabin_pricing,
            request.cabins_needed,
            deposit_amount=Decimal(str(cruise.deposit_amount)),
            cost=Decimal(str(cruise.cost)),
        )
        cruise.cabin_pricing = normalized
        sync_cruise_totals_from_cabin_pricing(cruise)
        if cruise.cabin_rooms:
            for index, entry in enumerate(normalized):
                if index < len(cruise.cabin_rooms):
                    cruise.cabin_rooms[index]["deposit_amount"] = entry["deposit_amount"]
                    cruise.cabin_rooms[index]["cost"] = entry["cost"]

    if cabin_hold_reservation_ids is not None:
        cruise.cabin_hold_reservation_ids = cabin_hold_reservation_ids

    if room_passenger_ids is not None or passenger_ids is not None:
        normalized_room_passenger_ids = normalize_room_passenger_ids(
            room_passenger_ids,
            passenger_ids,
            request.cabins_needed,
        )
        sync_proposed_cruise_room_passengers(
            db,
            cruise,
            normalized_room_passenger_ids,
            request_id,
            request.cabins_needed,
        )

    cruise.updated_by_id = current_user.id
    touch_request(request, current_user)
    db.commit()
    if rollup_refresh_triggers_on_cruise_status(next_status):
        schedule_agency_rollup_refresh(request.agency_id)
    cruise = load_proposed_cruise(db, cruise.id)
    return proposed_cruise_to_read(cruise, request.cabins_needed)
