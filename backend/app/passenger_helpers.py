from sqlalchemy import String, cast, func, or_
from sqlalchemy.orm import Session

from app.models import Passenger, RequestPassenger
from app.services.agency_service import get_travel_request_for_agency
from app.tenant_context import require_current_agency_id

CLIENTS_PAGE_SIZE_DEFAULT = 25
CLIENTS_PAGE_SIZE_MAX = 100


def _client_search_filters(term: str) -> list:
    pattern = f"%{term}%"
    phone_digits = "".join(character for character in term if character.isdigit())
    filters = [
        Passenger.first_name.ilike(pattern),
        Passenger.last_name.ilike(pattern),
        Passenger.email.ilike(pattern),
        Passenger.phone.ilike(pattern),
        func.concat(Passenger.first_name, " ", Passenger.last_name).ilike(pattern),
        cast(Passenger.date_of_birth, String).ilike(pattern),
    ]
    if phone_digits:
        filters.append(Passenger.phone.ilike(f"%{phone_digits}%"))
    return filters


def _clients_with_request_counts_query(db: Session):
    return (
        db.query(Passenger, func.count(RequestPassenger.id))
        .outerjoin(RequestPassenger, RequestPassenger.passenger_id == Passenger.id)
        .group_by(Passenger.id)
    )


def create_passenger_record(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str | None,
    phone: str | None,
    date_of_birth,
    created_by_id: int | None,
) -> Passenger:
    passenger = Passenger(
        agency_id=require_current_agency_id(),
        first_name=first_name,
        last_name=last_name,
        email=email.strip() if email and email.strip() else None,
        phone=phone.strip() if phone and phone.strip() else None,
        date_of_birth=date_of_birth,
        created_by_id=created_by_id,
        is_active=True,
    )
    db.add(passenger)
    db.flush()
    return passenger


def _normalize_optional_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def create_client_record(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str | None,
    phone: str | None,
    date_of_birth,
    address_line_1: str | None = None,
    address_line_2: str | None = None,
    city: str | None = None,
    state_or_province: str | None = None,
    postal_code: str | None = None,
    country: str | None = None,
    qualifiers: list[str] | None = None,
    has_annual_insurance: bool = False,
    annual_insurance_expires_at=None,
    annual_insurance_policy_number: str | None = None,
    created_by_id: int | None,
) -> Passenger:
    passenger = Passenger(
        agency_id=require_current_agency_id(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=_normalize_optional_text(email),
        phone=_normalize_optional_text(phone),
        date_of_birth=date_of_birth,
        address_line_1=_normalize_optional_text(address_line_1),
        address_line_2=_normalize_optional_text(address_line_2),
        city=_normalize_optional_text(city),
        state_or_province=_normalize_optional_text(state_or_province),
        postal_code=_normalize_optional_text(postal_code),
        country=_normalize_optional_text(country),
        qualifiers=qualifiers or [],
        has_annual_insurance=has_annual_insurance,
        annual_insurance_expires_at=annual_insurance_expires_at if has_annual_insurance else None,
        annual_insurance_policy_number=_normalize_optional_text(annual_insurance_policy_number)
        if has_annual_insurance
        else None,
        created_by_id=created_by_id,
        is_active=True,
    )
    db.add(passenger)
    db.flush()
    return passenger


def get_passenger_or_none(db: Session, passenger_id: int) -> Passenger | None:
    return db.get(Passenger, passenger_id)


def list_passengers_with_request_counts(db: Session) -> list[tuple[Passenger, int]]:
    return (
        _clients_with_request_counts_query(db)
        .order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.asc())
        .all()
    )


def search_clients_with_request_counts(
    db: Session,
    *,
    query: str = "",
    page: int = 1,
    page_size: int = CLIENTS_PAGE_SIZE_DEFAULT,
) -> tuple[list[tuple[Passenger, int]], int, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, CLIENTS_PAGE_SIZE_MAX))

    registry_count = db.query(Passenger).count()
    base = _clients_with_request_counts_query(db)
    term = query.strip()
    if term:
        base = base.filter(or_(*_client_search_filters(term)))

    total = base.order_by(None).count()
    rows = (
        base.order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total, registry_count


def get_passenger_request_count(db: Session, passenger_id: int) -> int:
    return (
        db.query(RequestPassenger)
        .filter(RequestPassenger.passenger_id == passenger_id)
        .count()
    )


def deactivate_passenger_record(db: Session, passenger: Passenger) -> None:
    passenger.is_active = False


def activate_passenger_record(db: Session, passenger: Passenger) -> None:
    passenger.is_active = True


def get_request_passenger_link(
    db: Session,
    request_id: int,
    passenger_id: int,
) -> RequestPassenger | None:
    return (
        db.query(RequestPassenger)
        .filter(
            RequestPassenger.travel_request_id == request_id,
            RequestPassenger.passenger_id == passenger_id,
        )
        .first()
    )


def attach_passenger_to_request(
    db: Session,
    request_id: int,
    passenger_id: int,
    *,
    is_primary: bool = False,
    qualifiers: list[str] | None = None,
) -> RequestPassenger:
    passenger = db.get(Passenger, passenger_id)
    if passenger is None:
        raise ValueError("Passenger not found.")
    if not passenger.is_active:
        raise ValueError("Inactive clients cannot be added to a request.")

    get_travel_request_for_agency(db, request_id, passenger.agency_id)

    if get_request_passenger_link(db, request_id, passenger_id) is not None:
        raise ValueError("This passenger is already attached to the request.")

    link = RequestPassenger(
        travel_request_id=request_id,
        passenger_id=passenger_id,
        is_primary=is_primary,
        qualifiers=qualifiers or [],
    )
    db.add(link)
    db.flush()
    return link


def search_passengers(db: Session, query: str, *, limit: int = 20) -> list[Passenger]:
    term = query.strip()
    base_query = db.query(Passenger).filter(Passenger.is_active.is_(True))
    if not term:
        return (
            base_query.order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.desc())
            .limit(limit)
            .all()
        )

    pattern = f"%{term}%"
    phone_digits = "".join(character for character in term if character.isdigit())
    filters = [
        Passenger.first_name.like(pattern),
        Passenger.last_name.like(pattern),
        Passenger.email.like(pattern),
        Passenger.phone.like(pattern),
        func.concat(Passenger.first_name, " ", Passenger.last_name).like(pattern),
    ]
    if phone_digits:
        filters.append(Passenger.phone.like(f"%{phone_digits}%"))

    return (
        base_query.filter(or_(*filters))
        .order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.desc())
        .limit(limit)
        .all()
    )
