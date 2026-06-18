from app.models import ProposedCruise, RequestPassenger
from app.proposed_cruise_helpers import cabin_rooms_from_cruise
from app.schemas import ProposedCruiseRead, RequestPassengerRead


def request_passenger_to_read(passenger: RequestPassenger) -> RequestPassengerRead:
    return RequestPassengerRead.model_validate(passenger)


def build_room_passengers_from_links(
    cruise: ProposedCruise,
    cabins_needed: int,
) -> list[list[RequestPassengerRead]]:
    safe_cabins_needed = max(1, cabins_needed)
    rooms: list[list[RequestPassengerRead]] = [[] for _ in range(safe_cabins_needed)]
    for link in sorted(cruise.passenger_links, key=lambda item: (item.cabin_index, item.id)):
        if 0 <= link.cabin_index < safe_cabins_needed:
            rooms[link.cabin_index].append(request_passenger_to_read(link.request_passenger))
    return rooms


def proposed_cruise_to_read(cruise: ProposedCruise, cabins_needed: int = 1) -> ProposedCruiseRead:
    safe_cabins_needed = max(1, cabins_needed)
    room_passengers = build_room_passengers_from_links(cruise, safe_cabins_needed)
    flat_passengers = [passenger for room in room_passengers for passenger in room]
    cabin_rooms = cabin_rooms_from_cruise(cruise, safe_cabins_needed)
    base = ProposedCruiseRead.model_validate(cruise)
    return base.model_copy(
        update={
            "passengers": flat_passengers,
            "room_passengers": room_passengers,
            "cabin_rooms": cabin_rooms,
        }
    )
