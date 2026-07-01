from app.models import TravelRequest, TravelRequestGroupBooking
from app.services.group_inventory_reservation_service import build_group_inventory_reservation_increments


def test_build_group_inventory_reservation_increments_from_booking_rows():
    request = TravelRequest(
        id=1,
        group_inventory_id="legacy-inv",
        cabins_needed=3,
        group_bookings=[
            TravelRequestGroupBooking(
                id="booking-1",
                travel_request_id=1,
                group_inventory_id="inv-a",
                cabins_requested=2,
            ),
            TravelRequestGroupBooking(
                id="booking-2",
                travel_request_id=1,
                group_inventory_id="inv-b",
                cabins_requested=1,
            ),
        ],
    )

    assert build_group_inventory_reservation_increments(request) == {
        "inv-a": 2,
        "inv-b": 1,
    }


def test_build_group_inventory_reservation_increments_legacy_fallback():
    request = TravelRequest(
        id=1,
        group_inventory_id="legacy-inv",
        cabins_needed=3,
        group_bookings=[],
    )

    assert build_group_inventory_reservation_increments(request) == {"legacy-inv": 3}


def test_build_group_inventory_reservation_increments_skips_unlinked_requests():
    request = TravelRequest(id=1, group_bookings=[])

    assert build_group_inventory_reservation_increments(request) == {}
