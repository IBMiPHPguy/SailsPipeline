from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import Passenger, RequestPassenger


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


def get_passenger_or_none(db: Session, passenger_id: int) -> Passenger | None:
    return db.get(Passenger, passenger_id)


def list_passengers_with_request_counts(db: Session) -> list[tuple[Passenger, int]]:
    return (
        db.query(Passenger, func.count(RequestPassenger.id))
        .outerjoin(RequestPassenger, RequestPassenger.passenger_id == Passenger.id)
        .group_by(Passenger.id)
        .order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.asc())
        .all()
    )


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
