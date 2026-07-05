from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.audit_helpers import (
    PASSENGER_AUDIT_FIELDS,
    TRAVEL_REQUEST_AUDIT_FIELDS,
    apply_updates,
    collect_field_changes,
    record_passenger_field_changes,
    record_travel_request_field_changes,
)
from app.models import Passenger, ProposedCruise, ProposedCruisePassenger, RequestPassenger, TravelRequest, User
from app.services.agency_service import NOT_FOUND
from app.tenant_context import get_current_agency_id, set_current_agency_id


def load_request_passenger(db: Session, link_id: int) -> RequestPassenger:
    return (
        db.query(RequestPassenger)
        .options(
            joinedload(RequestPassenger.passenger).selectinload(Passenger.cruise_loyalty_numbers),
        )
        .filter(RequestPassenger.id == link_id)
        .one()
    )


def get_request_passenger_for_agency(
    db: Session,
    link_id: int,
    agency_id: str,
    *,
    travel_request_id: int | None = None,
) -> RequestPassenger:
    previous_agency_id = get_current_agency_id()
    set_current_agency_id(agency_id)
    try:
        query = (
            db.query(RequestPassenger)
            .options(
                joinedload(RequestPassenger.passenger).selectinload(Passenger.cruise_loyalty_numbers),
            )
            .join(TravelRequest, TravelRequest.id == RequestPassenger.travel_request_id)
            .filter(
                RequestPassenger.id == link_id,
                TravelRequest.agency_id == agency_id,
            )
        )
        if travel_request_id is not None:
            query = query.filter(RequestPassenger.travel_request_id == travel_request_id)
        link = query.first()
    finally:
        set_current_agency_id(previous_agency_id)
    if link is None:
        raise NOT_FOUND
    return link


def detach_request_passenger_from_proposed_cruises(
    db: Session,
    *,
    request_passenger_id: int,
    request_id: int,
) -> int:
    cruise_ids = select(ProposedCruise.id).where(ProposedCruise.travel_request_id == request_id)
    return (
        db.query(ProposedCruisePassenger)
        .filter(
            ProposedCruisePassenger.request_passenger_id == request_passenger_id,
            ProposedCruisePassenger.proposed_cruise_id.in_(cruise_ids),
        )
        .delete(synchronize_session=False)
    )


def get_primary_passenger(db: Session, request_id: int) -> RequestPassenger | None:
    primary = (
        db.query(RequestPassenger)
        .options(
            joinedload(RequestPassenger.passenger).selectinload(Passenger.cruise_loyalty_numbers),
        )
        .filter(
            RequestPassenger.travel_request_id == request_id,
            RequestPassenger.is_primary.is_(True),
        )
        .first()
    )
    if primary is not None:
        return primary
    return (
        db.query(RequestPassenger)
        .options(
            joinedload(RequestPassenger.passenger).selectinload(Passenger.cruise_loyalty_numbers),
        )
        .filter(RequestPassenger.travel_request_id == request_id)
        .order_by(RequestPassenger.id.asc())
        .first()
    )


def sync_primary_passenger_from_request(
    request: TravelRequest,
    db: Session,
    current_user: User,
) -> None:
    primary = get_primary_passenger(db, request.id)
    if primary is None:
        return
    sync_updates = {
        "first_name": request.first_name,
        "last_name": request.last_name,
        "email": request.email,
        "phone": request.phone,
    }
    passenger_changes = collect_field_changes(primary, sync_updates, PASSENGER_AUDIT_FIELDS)
    record_passenger_field_changes(db, primary, passenger_changes, current_user)
    apply_updates(primary, sync_updates)


def sync_request_from_primary_passenger(
    db: Session,
    request: TravelRequest,
    passenger: RequestPassenger,
    current_user: User,
) -> None:
    primary = get_primary_passenger(db, request.id)
    if primary is None or primary.id != passenger.id:
        return
    sync_updates = {
        "first_name": passenger.first_name,
        "last_name": passenger.last_name,
        "email": passenger.email,
        "phone": passenger.phone,
    }
    request_changes = collect_field_changes(request, sync_updates, TRAVEL_REQUEST_AUDIT_FIELDS)
    record_travel_request_field_changes(db, request, request_changes, current_user)
    apply_updates(request, sync_updates)
