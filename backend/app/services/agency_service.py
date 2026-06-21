from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Agency, Passenger, TravelRequest
from app.tenant_constants import DEFAULT_AGENCY_ID, DEFAULT_AGENCY_NAME, DEFAULT_AGENCY_SLUG

T = TypeVar("T")

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def ensure_default_agency(db: Session) -> Agency:
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    if agency is not None:
        return agency

    agency = Agency(
        id=DEFAULT_AGENCY_ID,
        name=DEFAULT_AGENCY_NAME,
        slug=DEFAULT_AGENCY_SLUG,
        is_active=True,
    )
    db.add(agency)
    db.flush()
    return agency


def assert_same_agency(*, entity_agency_id: str, expected_agency_id: str) -> None:
    if entity_agency_id != expected_agency_id:
        raise NOT_FOUND


def get_travel_request_for_agency(db: Session, request_id: int, agency_id: str) -> TravelRequest:
    request = db.get(TravelRequest, request_id)
    if request is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=request.agency_id, expected_agency_id=agency_id)
    return request


def get_passenger_for_agency(db: Session, passenger_id: int, agency_id: str) -> Passenger:
    passenger = db.get(Passenger, passenger_id)
    if passenger is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=passenger.agency_id, expected_agency_id=agency_id)
    return passenger


def assert_child_belongs_to_request(
    *,
    child_agency_id: str,
    child_travel_request_id: int,
    request_id: int,
    agency_id: str,
) -> None:
    if child_travel_request_id != request_id:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=child_agency_id, expected_agency_id=agency_id)


def require_record_for_agency(
    record: T | None,
    *,
    agency_id: str,
    agency_id_attr: str = "agency_id",
) -> T:
    if record is None:
        raise NOT_FOUND
    record_agency_id = getattr(record, agency_id_attr, None)
    if record_agency_id is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=record_agency_id, expected_agency_id=agency_id)
    return record
