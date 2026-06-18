from __future__ import annotations

from decimal import Decimal

from app.models import ProposedCruise, default_proposed_cruise_includes
from app.schemas import CabinPricingEntry, ProposedCruiseIncludes, ProposedCruiseRoom


def default_proposed_cruise_includes_dict() -> dict:
    return default_proposed_cruise_includes()


def serialize_includes_for_storage(includes: dict | ProposedCruiseIncludes) -> dict:
    if hasattr(includes, "model_dump"):
        return includes.model_dump(mode="json")
    payload = dict(includes or default_proposed_cruise_includes_dict())
    for key in ("excursion_credit", "onboard_credit", "gift_obc"):
        credit = dict(payload.get(key) or {})
        amount = credit.get("amount")
        if amount is not None:
            credit["amount"] = str(amount)
        payload[key] = credit
    return payload


def normalize_cabin_pricing_list(
    raw: list | None,
    cabins_needed: int,
    *,
    deposit_amount: Decimal,
    cost: Decimal,
) -> list[dict]:
    safe_cabins_needed = max(1, cabins_needed)
    source = raw or []
    entries: list[dict] = []
    per_deposit = (deposit_amount / safe_cabins_needed).quantize(Decimal("0.01"))
    per_cost = (cost / safe_cabins_needed).quantize(Decimal("0.01"))

    for index in range(safe_cabins_needed):
        if index < len(source):
            entry = CabinPricingEntry.model_validate(source[index])
            entries.append(
                {
                    "deposit_amount": str(entry.deposit_amount),
                    "cost": str(entry.cost),
                }
            )
        else:
            entries.append(
                {
                    "deposit_amount": str(per_deposit),
                    "cost": str(per_cost),
                }
            )

    return entries


def normalize_cabin_rooms_list(
    raw: list | None,
    cabins_needed: int,
    *,
    room_category: str,
    room_number: str,
    passengers_in_room: int,
    deposit_amount: Decimal,
    cost: Decimal,
    includes: dict | ProposedCruiseIncludes,
    cabin_pricing: list | None,
) -> list[dict]:
    safe_cabins_needed = max(1, cabins_needed)
    includes_payload = serialize_includes_for_storage(includes)
    pricing = normalize_cabin_pricing_list(
        cabin_pricing,
        safe_cabins_needed,
        deposit_amount=deposit_amount,
        cost=cost,
    )
    source = raw or []
    rooms: list[dict] = []

    for index in range(safe_cabins_needed):
        if index < len(source):
            room = ProposedCruiseRoom.model_validate(source[index])
            entry = room.model_dump()
            entry["includes"] = serialize_includes_for_storage(room.includes)
        else:
            entry = {
                "room_category": room_category,
                "room_number": room_number,
                "passengers_in_room": passengers_in_room,
                "deposit_amount": pricing[index]["deposit_amount"],
                "commission": "0",
                "cost": pricing[index]["cost"],
                "includes": includes_payload,
            }
        rooms.append(
            {
                "room_category": entry["room_category"],
                "room_number": entry["room_number"],
                "passengers_in_room": entry["passengers_in_room"],
                "deposit_amount": str(entry["deposit_amount"]),
                "commission": str(entry.get("commission", 0)),
                "cost": str(entry["cost"]),
                "includes": entry["includes"],
            }
        )

    return rooms


def sync_cruise_totals_from_cabin_pricing(cruise: ProposedCruise) -> None:
    if not cruise.cabin_pricing:
        return

    deposit_total = Decimal("0")
    cost_total = Decimal("0")
    for item in cruise.cabin_pricing:
        if not isinstance(item, dict):
            continue
        deposit_total += Decimal(str(item.get("deposit_amount", 0)))
        cost_total += Decimal(str(item.get("cost", 0)))

    cruise.deposit_amount = deposit_total
    cruise.cost = cost_total


def sync_cruise_from_cabin_rooms(cruise: ProposedCruise, cabin_rooms: list[dict]) -> None:
    cruise.cabin_rooms = cabin_rooms
    cruise.cabin_pricing = [
        {
            "deposit_amount": room["deposit_amount"],
            "cost": room["cost"],
        }
        for room in cabin_rooms
    ]
    sync_cruise_totals_from_cabin_pricing(cruise)
    if cabin_rooms:
        first_room = cabin_rooms[0]
        cruise.room_category = first_room["room_category"]
        cruise.room_number = first_room["room_number"]
        cruise.passengers_in_room = first_room["passengers_in_room"]
        cruise.includes = first_room.get("includes") or default_proposed_cruise_includes_dict()


def flatten_room_passenger_ids(room_passenger_ids: list[list[int]]) -> list[int]:
    return [passenger_id for room in room_passenger_ids for passenger_id in room]


def normalize_room_passenger_ids(
    room_passenger_ids: list[list[int]] | None,
    passenger_ids: list[int] | None,
    cabins_needed: int,
) -> list[list[int]]:
    safe_cabins_needed = max(1, cabins_needed)
    if room_passenger_ids is not None:
        normalized: list[list[int]] = []
        for cabin_index in range(safe_cabins_needed):
            room = room_passenger_ids[cabin_index] if cabin_index < len(room_passenger_ids) else []
            normalized.append(list(room))
        return normalized

    normalized = [[] for _ in range(safe_cabins_needed)]
    if passenger_ids:
        normalized[0] = list(passenger_ids)
    return normalized


def passengers_in_room_limits_for_cruise(cruise: ProposedCruise, cabins_needed: int) -> list[int]:
    safe_cabins_needed = max(1, cabins_needed)
    if cruise.cabin_rooms:
        limits = [
            int(room.get("passengers_in_room", cruise.passengers_in_room))
            for room in cruise.cabin_rooms[:safe_cabins_needed]
        ]
        while len(limits) < safe_cabins_needed:
            limits.append(cruise.passengers_in_room)
        return limits
    return [cruise.passengers_in_room for _ in range(safe_cabins_needed)]


def cabin_rooms_from_cruise(cruise: ProposedCruise, cabins_needed: int) -> list[ProposedCruiseRoom]:
    defaults = default_proposed_cruise_includes_dict()
    includes = cruise.includes or defaults
    deposit_amount = Decimal(str(cruise.deposit_amount))
    cost = Decimal(str(cruise.cost))
    source = cruise.cabin_rooms if cruise.cabin_rooms else None

    return [
        ProposedCruiseRoom.model_validate(room)
        for room in normalize_cabin_rooms_list(
            source,
            cabins_needed,
            room_category=cruise.room_category,
            room_number=cruise.room_number,
            passengers_in_room=cruise.passengers_in_room,
            deposit_amount=deposit_amount,
            cost=cost,
            includes=includes,
            cabin_pricing=cruise.cabin_pricing,
        )
    ]
