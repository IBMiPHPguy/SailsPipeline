from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit_helpers import (
    PASSENGER_AUDIT_FIELDS,
    apply_updates,
    collect_field_changes,
    record_passenger_deletion,
    record_passenger_field_changes,
)
from app.database import get_db
from app.deps import get_current_user
from app.models import Passenger, RequestPassenger, User
from app.passenger_helpers import (
    activate_passenger_record,
    attach_passenger_to_request,
    create_client_record,
    create_passenger_record,
    deactivate_passenger_record,
    get_passenger_or_none,
    search_clients_with_request_counts,
    search_passengers,
)
from app.pagination import DEFAULT_PAGE_SIZE, PAGE_SIZE_MAX
from app.schemas import (
    ClientsPageRead,
    PassengerCreate,
    PassengerListRead,
    PassengerRead,
    PassengerUpdate,
    RequestPassengerCreate,
    RequestPassengerRead,
    RequestPassengerUpdate,
)
from app.services.agency_service import get_passenger_for_agency
from app.services.passenger_service import (
    detach_request_passenger_from_proposed_cruises,
    get_request_passenger_for_agency,
    sync_request_from_primary_passenger,
)
from app.services.request_service import closed_requests_total_pages, get_open_request, touch_request

router = APIRouter(prefix="/api/passengers", tags=["passengers"])
request_passengers_router = APIRouter(prefix="/api/requests", tags=["request-passengers"])


@router.get("/search", response_model=list[PassengerRead])
def search_passenger_registry(
    q: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Passenger]:
    safe_limit = max(1, min(limit, 50))
    return search_passengers(db, q, limit=safe_limit)


@router.get("", response_model=ClientsPageRead)
def list_passenger_registry(
    q: str = "",
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientsPageRead:
    normalized_page_size = max(1, min(page_size, PAGE_SIZE_MAX))
    rows, total, registry_count = search_clients_with_request_counts(
        db,
        query=q,
        page=page,
        page_size=normalized_page_size,
    )
    return ClientsPageRead(
        items=[
            PassengerListRead(
                id=passenger.id,
                first_name=passenger.first_name,
                last_name=passenger.last_name,
                email=passenger.email,
                phone=passenger.phone,
                date_of_birth=passenger.date_of_birth,
                qualifiers=passenger.qualifiers or [],
                is_active=passenger.is_active,
                has_annual_insurance=passenger.has_annual_insurance,
                request_count=request_count,
            )
            for passenger, request_count in rows
        ],
        total=total,
        registry_count=registry_count,
        page=max(1, page),
        page_size=normalized_page_size,
        total_pages=closed_requests_total_pages(total, normalized_page_size),
    )


@router.post("", response_model=PassengerRead, status_code=201)
def create_passenger_registry(
    payload: PassengerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Passenger:
    passenger = create_client_record(
        db,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=str(payload.email) if payload.email is not None else None,
        phone=payload.phone,
        date_of_birth=payload.date_of_birth,
        address_line_1=payload.address_line_1,
        address_line_2=payload.address_line_2,
        city=payload.city,
        state_or_province=payload.state_or_province,
        postal_code=payload.postal_code,
        country=payload.country,
        qualifiers=payload.qualifiers,
        has_annual_insurance=payload.has_annual_insurance,
        annual_insurance_expires_at=payload.annual_insurance_expires_at,
        annual_insurance_policy_number=payload.annual_insurance_policy_number,
        created_by_id=current_user.id,
    )
    if payload.cruise_loyalty_numbers:
        from app.services.passenger_loyalty_service import sync_passenger_loyalty_numbers

        try:
            sync_passenger_loyalty_numbers(
                db,
                passenger=passenger,
                entries=[entry.model_dump() for entry in payload.cruise_loyalty_numbers],
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    db.commit()
    db.refresh(passenger)
    return passenger


@router.get("/{passenger_id}", response_model=PassengerRead)
def get_passenger_registry(
    passenger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Passenger:
    return get_passenger_for_agency(db, passenger_id, current_user.agency_id)


@router.patch("/{passenger_id}", response_model=PassengerRead)
def update_passenger_registry(
    passenger_id: int,
    payload: PassengerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Passenger:
    passenger = get_passenger_for_agency(db, passenger_id, current_user.agency_id)

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("has_annual_insurance") is False:
        updates["annual_insurance_expires_at"] = None
        updates["annual_insurance_policy_number"] = None
    loyalty_entries = updates.pop("cruise_loyalty_numbers", None)
    for field, value in updates.items():
        setattr(passenger, field, value)
    if loyalty_entries is not None:
        from app.services.passenger_loyalty_service import sync_passenger_loyalty_numbers

        try:
            sync_passenger_loyalty_numbers(
                db,
                passenger=passenger,
                entries=[entry for entry in loyalty_entries],
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    passenger.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(passenger)
    return passenger


@router.post("/{passenger_id}/deactivate", response_model=PassengerRead)
def deactivate_passenger_registry(
    passenger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Passenger:
    passenger = get_passenger_for_agency(db, passenger_id, current_user.agency_id)
    if not passenger.is_active:
        raise HTTPException(status_code=400, detail="Client is already inactive.")

    deactivate_passenger_record(db, passenger)
    db.commit()
    db.refresh(passenger)
    return passenger


@router.post("/{passenger_id}/activate", response_model=PassengerRead)
def activate_passenger_registry(
    passenger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Passenger:
    passenger = get_passenger_for_agency(db, passenger_id, current_user.agency_id)
    if passenger.is_active:
        raise HTTPException(status_code=400, detail="Client is already active.")

    activate_passenger_record(db, passenger)
    db.commit()
    db.refresh(passenger)
    return passenger


@request_passengers_router.post("/{request_id}/passengers", response_model=RequestPassengerRead, status_code=201)
def add_passenger(
    request_id: int,
    payload: RequestPassengerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestPassenger:
    request = get_open_request(db, request_id, current_user)
    try:
        if payload.passenger_id is not None:
            passenger = get_passenger_for_agency(db, payload.passenger_id, current_user.agency_id)
            if not passenger.is_active:
                raise HTTPException(status_code=400, detail="Inactive clients cannot be added to a request.")
            link = attach_passenger_to_request(
                db,
                request_id,
                passenger.id,
                qualifiers=payload.qualifiers,
            )
        else:
            passenger = create_passenger_record(
                db,
                first_name=payload.first_name.strip(),
                last_name=payload.last_name.strip(),
                email=str(payload.email) if payload.email is not None else None,
                phone=payload.phone,
                date_of_birth=payload.date_of_birth,
                created_by_id=current_user.id,
            )
            link = attach_passenger_to_request(
                db,
                request_id,
                passenger.id,
                qualifiers=payload.qualifiers,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    touch_request(request, current_user)
    db.commit()
    return get_request_passenger_for_agency(
        db,
        link.id,
        current_user.agency_id,
        travel_request_id=request_id,
    )


@request_passengers_router.patch(
    "/{request_id}/passengers/{passenger_id}",
    response_model=RequestPassengerRead,
)
def update_passenger(
    request_id: int,
    passenger_id: int,
    payload: RequestPassengerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RequestPassenger:
    request = get_open_request(db, request_id, current_user)
    passenger = get_request_passenger_for_agency(
        db,
        passenger_id,
        current_user.agency_id,
        travel_request_id=request_id,
    )

    updates = payload.model_dump(exclude_unset=True)
    passenger_changes = collect_field_changes(passenger, updates, PASSENGER_AUDIT_FIELDS)
    record_passenger_field_changes(db, passenger, passenger_changes, current_user)
    loyalty_entries = updates.pop("cruise_loyalty_numbers", None)
    apply_updates(passenger, updates)
    if loyalty_entries is not None:
        from app.services.passenger_loyalty_service import sync_passenger_loyalty_numbers

        try:
            sync_passenger_loyalty_numbers(
                db,
                passenger=passenger.passenger,
                entries=[entry for entry in loyalty_entries],
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    sync_request_from_primary_passenger(db, request, passenger, current_user)
    touch_request(request, current_user)
    db.commit()
    return get_request_passenger_for_agency(
        db,
        passenger.id,
        current_user.agency_id,
        travel_request_id=request_id,
    )


@request_passengers_router.delete("/{request_id}/passengers/{passenger_id}", status_code=204)
def delete_passenger(
    request_id: int,
    passenger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    request = get_open_request(db, request_id, current_user)
    passenger = get_request_passenger_for_agency(
        db,
        passenger_id,
        current_user.agency_id,
        travel_request_id=request_id,
    )

    passenger_count = (
        db.query(RequestPassenger).filter(RequestPassenger.travel_request_id == request_id).count()
    )
    if passenger_count <= 1:
        raise HTTPException(status_code=400, detail="At least one passenger is required.")
    if passenger.is_primary:
        raise HTTPException(
            status_code=400,
            detail="The primary passenger cannot be removed from the request.",
        )

    detach_request_passenger_from_proposed_cruises(
        db,
        request_passenger_id=passenger.id,
        request_id=request_id,
    )
    record_passenger_deletion(db, passenger, current_user)
    db.delete(passenger)
    touch_request(request, current_user)
    db.commit()
