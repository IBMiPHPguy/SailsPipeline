"""Seed proposed cruise + cabin rooms from group block intake."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import AgencyGroup, TravelRequest, User
from app.schemas import ProposedCruiseCreate, ProposedCruiseIncludes, ProposedCruiseRoom
from app.services.proposed_cruise_record_service import (
    assign_default_room_passenger_ids,
    create_proposed_cruise_record,
)


def _room_category_label(*, cabin_type: str, cabin_category: str, cabin_description: str | None) -> str:
    description = (cabin_description or "").strip()
    if description:
        label = f"{description} ({cabin_category})"
    else:
        label = f"{cabin_type} ({cabin_category})"
    return label[:120]


def distribute_passengers_across_cabins(passengers: int, cabins: int) -> list[int]:
    safe_cabins = max(1, cabins)
    safe_passengers = max(safe_cabins, passengers)
    base, extra = divmod(safe_passengers, safe_cabins)
    return [base + (1 if index < extra else 0) for index in range(safe_cabins)]


def default_group_payment_due_dates(departure_date: date) -> tuple[date, date]:
    today = date.today()
    deposit_due = departure_date - timedelta(days=90)
    if deposit_due < today:
        deposit_due = today
    final_due = departure_date - timedelta(days=30)
    if final_due < deposit_due:
        final_due = deposit_due
    return deposit_due, final_due


def build_group_intake_cabin_rooms(
    *,
    group_booking_rows: list[dict],
    passengers: int,
) -> list[ProposedCruiseRoom]:
    expanded: list[ProposedCruiseRoom] = []
    for row in group_booking_rows:
        inventory = row["inventory"]
        room_category = _room_category_label(
            cabin_type=inventory.cabin_type,
            cabin_category=inventory.cabin_category,
            cabin_description=inventory.cabin_description,
        )
        price = Decimal(str(inventory.price_per_cabin))
        deposit = Decimal(str(inventory.deposit_per_cabin))
        for _ in range(int(row["cabins_requested"])):
            expanded.append(
                {
                    "room_category": room_category,
                    "room_number": "TBD",
                    "passengers_in_room": 1,
                    "deposit_amount": deposit,
                    "commission": Decimal("0"),
                    "cost": price,
                    "includes": ProposedCruiseIncludes(),
                }
            )

    if not expanded:
        return []

    passenger_counts = distribute_passengers_across_cabins(passengers, len(expanded))
    rooms: list[ProposedCruiseRoom] = []
    for index, room in enumerate(expanded):
        rooms.append(
            ProposedCruiseRoom.model_validate(
                {
                    **room,
                    "passengers_in_room": passenger_counts[index],
                }
            )
        )
    return rooms


def build_group_intake_itinerary_details(group: AgencyGroup) -> str | None:
    parts: list[str] = []
    if group.group_id_code:
        parts.append(f"Group ID: {group.group_id_code}")
    if group.group_amenities and str(group.group_amenities).strip():
        parts.append(str(group.group_amenities).strip())
    if not parts:
        return None
    return "\n\n".join(parts)


def build_proposed_cruise_create_from_group_intake(
    *,
    request: TravelRequest,
    group: AgencyGroup,
    group_booking_rows: list[dict],
) -> ProposedCruiseCreate | None:
    cabin_rooms = build_group_intake_cabin_rooms(
        group_booking_rows=group_booking_rows,
        passengers=request.passengers,
    )
    if not cabin_rooms:
        return None

    nights = (group.disembarkation_date - group.sailing_date).days
    if nights < 1:
        nights = 1

    total_cost = sum(room.cost for room in cabin_rooms)
    total_deposit = sum(room.deposit_amount for room in cabin_rooms)
    deposit_due, final_due = default_group_payment_due_dates(group.sailing_date)
    first_room = cabin_rooms[0]

    return ProposedCruiseCreate(
        departure_date=group.sailing_date,
        cruise_line=group.cruise_line,
        ship=group.ship_name,
        number_of_nights=nights,
        itinerary_name=group.group_name[:160],
        itinerary_details=build_group_intake_itinerary_details(group),
        room_category=first_room.room_category,
        room_number=first_room.room_number,
        passengers_in_room=first_room.passengers_in_room,
        deposit_amount=total_deposit,
        deposit_due_date=deposit_due,
        final_payment_due_date=final_due,
        cost=total_cost,
        includes=ProposedCruiseIncludes(),
        cabin_rooms=cabin_rooms,
        passenger_ids=[],
        room_passenger_ids=[],
    )


def seed_proposed_cruise_from_group_intake(
    db: Session,
    *,
    request: TravelRequest,
    group: AgencyGroup,
    group_booking_rows: list[dict],
    current_user: User,
) -> None:
    payload = build_proposed_cruise_create_from_group_intake(
        request=request,
        group=group,
        group_booking_rows=group_booking_rows,
    )
    if payload is None:
        return

    room_passenger_ids = assign_default_room_passenger_ids(
        db,
        request.id,
        payload.passengers_in_room,
        request.cabins_needed,
    )
    payload = payload.model_copy(update={"room_passenger_ids": room_passenger_ids, "passenger_ids": []})
    create_proposed_cruise_record(db, request, payload, current_user)
