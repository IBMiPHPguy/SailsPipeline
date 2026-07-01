from datetime import date
from decimal import Decimal

from app.models import AgencyGroup, AgencyGroupInventory
from app.services.group_intake_proposed_cruise_service import (
    build_group_intake_cabin_rooms,
    build_proposed_cruise_create_from_group_intake,
    distribute_passengers_across_cabins,
)


def _inventory(
    *,
    cabin_category: str,
    cabin_type: str,
    description: str | None,
    price: float,
    deposit: float = 0,
) -> AgencyGroupInventory:
    return AgencyGroupInventory(
        id="inv-1",
        group_id="group-1",
        cabin_category=cabin_category,
        cabin_type=cabin_type,
        cabin_description=description,
        price_per_cabin=price,
        deposit_per_cabin=deposit,
        cabins_allocated=10,
        cabins_reserved=0,
    )


def test_distribute_passengers_across_cabins():
    assert distribute_passengers_across_cabins(4, 2) == [2, 2]
    assert distribute_passengers_across_cabins(2, 3) == [1, 1, 1]
    assert distribute_passengers_across_cabins(5, 2) == [3, 2]


def test_build_group_intake_cabin_rooms_expands_inventory_rows():
    rows = [
        {
            "group_inventory_id": "inv-1",
            "cabins_requested": 2,
            "inventory": _inventory(
                cabin_category="VN",
                cabin_type="Ocean View",
                description="Partial view",
                price=1499,
                deposit=250,
            ),
        },
        {
            "group_inventory_id": "inv-2",
            "cabins_requested": 1,
            "inventory": _inventory(
                cabin_category="8C",
                cabin_type="Balcony",
                description=None,
                price=2199,
                deposit=300,
            ),
        },
    ]
    rooms = build_group_intake_cabin_rooms(group_booking_rows=rows, passengers=4)
    assert len(rooms) == 3
    assert rooms[0].room_category == "Partial view (VN)"
    assert rooms[0].cost == Decimal("1499")
    assert rooms[0].deposit_amount == Decimal("250")
    assert rooms[2].room_category == "Balcony (8C)"
    assert rooms[2].deposit_amount == Decimal("300")
    assert sum(room.passengers_in_room for room in rooms) >= 4


def test_build_proposed_cruise_create_from_group_intake():
    group = AgencyGroup(
        id="group-1",
        agency_id="agency-1",
        group_name="Alaska Alumni 2028",
        cruise_line="Holland America Line",
        ship_name="Nieuw Amsterdam",
        sailing_date=date(2028, 6, 1),
        disembarkation_date=date(2028, 6, 8),
        group_id_code="ALASKA-2028",
        group_amenities="Welcome reception",
        is_active=True,
    )

    class RequestStub:
        passengers = 4
        cabins_needed = 2

    payload = build_proposed_cruise_create_from_group_intake(
        request=RequestStub(),
        group=group,
        group_booking_rows=[
            {
                "cabins_requested": 2,
                "inventory": _inventory(
                    cabin_category="VN",
                    cabin_type="Ocean View",
                    description="Partial view",
                    price=1499,
                    deposit=250,
                ),
            }
        ],
    )

    assert payload is not None
    assert payload.departure_date == date(2028, 6, 1)
    assert payload.ship == "Nieuw Amsterdam"
    assert payload.number_of_nights == 7
    assert payload.itinerary_name == "Alaska Alumni 2028"
    assert "Welcome reception" in (payload.itinerary_details or "")
    assert len(payload.cabin_rooms) == 2
    assert payload.cost == Decimal("2998")
    assert payload.deposit_amount == Decimal("500")
