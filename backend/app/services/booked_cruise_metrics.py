from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.constants import (
    BOOKED_CRUISE_STATUSES,
    ACTIVE_PIPELINE_QUOTE_STATUSES,
    REQUEST_STATUS_OPEN,
)
from app.models import ProposedCruise, TravelRequest


def cruise_total_commission(cruise: ProposedCruise) -> Decimal:
    total = Decimal("0")
    for room in cruise.cabin_rooms or []:
        if not isinstance(room, dict):
            continue
        try:
            total += Decimal(str(room.get("commission") or 0))
        except Exception:
            continue
    return total


def booked_cruises_query(db: Session, agency_id: str) -> Query:
    return db.query(ProposedCruise).filter(
        ProposedCruise.agency_id == agency_id,
        ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
    )


def count_booked_cruises(db: Session, agency_id: str) -> int:
    return (
        db.query(func.count(ProposedCruise.id))
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
        )
        .scalar()
        or 0
    )


def sum_booked_cruise_volume(db: Session, agency_id: str) -> float:
    total = (
        db.query(func.coalesce(func.sum(ProposedCruise.cost), 0))
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
        )
        .scalar()
    )
    return float(total or 0)


def sum_booked_cruise_commission(db: Session, agency_id: str) -> float:
    cruises = booked_cruises_query(db, agency_id).all()
    return float(sum(cruise_total_commission(cruise) for cruise in cruises))


@dataclass(frozen=True)
class BookedCruiseAggregates:
    booking_count: int
    total_volume: float
    total_commission: float


def get_booked_cruise_aggregates(db: Session, agency_id: str) -> BookedCruiseAggregates:
    return BookedCruiseAggregates(
        booking_count=count_booked_cruises(db, agency_id),
        total_volume=sum_booked_cruise_volume(db, agency_id),
        total_commission=sum_booked_cruise_commission(db, agency_id),
    )


def load_booked_cruises(db: Session, agency_id: str) -> list[ProposedCruise]:
    return booked_cruises_query(db, agency_id).all()


def booked_cruise_line_aggregates(
    db: Session,
    agency_id: str,
    *,
    cruises: list[ProposedCruise] | None = None,
) -> list[tuple[str, int, float]]:
    if cruises is None:
        cruises = load_booked_cruises(db, agency_id)

    volume_by_line: dict[str, float] = {}
    count_by_line: dict[str, int] = {}
    for cruise in cruises:
        line = (cruise.cruise_line or "Unknown").strip() or "Unknown"
        count_by_line[line] = count_by_line.get(line, 0) + 1
        volume_by_line[line] = volume_by_line.get(line, 0.0) + float(cruise.cost or 0)

    return [
        (line, count_by_line[line], volume_by_line[line])
        for line in sorted(count_by_line.keys(), key=lambda name: (-count_by_line[name], name))
    ]


def sum_booked_cruise_financials(cruises: list[ProposedCruise]) -> tuple[float, float]:
    gross_total = sum(float(cruise.cost or 0) for cruise in cruises)
    commission_total = float(sum(cruise_total_commission(cruise) for cruise in cruises))
    return gross_total, commission_total


def calculate_open_pipeline_value(db: Session, *, agency_id: str | None = None) -> float:
    """Sum booked cruise costs on open requests; otherwise the highest active quote per request."""
    request_query = db.query(TravelRequest.id).filter(TravelRequest.status == REQUEST_STATUS_OPEN)
    if agency_id is not None:
        request_query = request_query.filter(TravelRequest.agency_id == agency_id)

    open_request_ids = [row[0] for row in request_query.all()]
    if not open_request_ids:
        return 0.0

    total = 0.0
    for request_id in open_request_ids:
        cruise_query = db.query(ProposedCruise).filter(
            ProposedCruise.travel_request_id == request_id,
            ProposedCruise.status.in_(ACTIVE_PIPELINE_QUOTE_STATUSES),
        )
        if agency_id is not None:
            cruise_query = cruise_query.filter(ProposedCruise.agency_id == agency_id)

        cruises = cruise_query.all()
        booked = [cruise for cruise in cruises if cruise.status in BOOKED_CRUISE_STATUSES]
        if booked:
            total += sum(float(cruise.cost or 0) for cruise in booked)
            continue

        active_costs = [float(cruise.cost or 0) for cruise in cruises]
        if active_costs:
            total += max(active_costs)

    return total
