from datetime import date
from decimal import Decimal

from app.constants import (
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
)
from app.models import ProposedCruise, TravelRequest, User
from app.security import hash_password
from app.services.booked_cruise_metrics import (
    count_booked_cruises,
    get_booked_cruise_aggregates,
    sum_booked_cruise_volume,
)
from app.tenant_constants import DEFAULT_AGENCY_ID


def _create_user(db, *, username: str) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()
    return user


def test_booked_cruise_metrics_sum_all_accepted_and_deposited_rows(db):
    user = _create_user(db, username="metrics-agent")
    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Multi",
        last_name="Booking",
        email="multi@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International", "Celebrity Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status="Open",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(request)
    db.flush()

    db.add_all(
        [
            ProposedCruise(
                agency_id=DEFAULT_AGENCY_ID,
                travel_request_id=request.id,
                departure_date=date(2026, 8, 1),
                cruise_line="Royal Caribbean International",
                ship="Wonder",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="1234",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 7, 1),
                cost=Decimal("5000.00"),
                cabin_rooms=[{"commission": "500.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
            ProposedCruise(
                agency_id=DEFAULT_AGENCY_ID,
                travel_request_id=request.id,
                departure_date=date(2026, 9, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="5678",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2026, 6, 15),
                final_payment_due_date=date(2026, 8, 15),
                cost=Decimal("4000.00"),
                cabin_rooms=[{"commission": "400.00"}],
                status=PROPOSED_CRUISE_STATUS_DEPOSITED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
        ]
    )
    db.commit()

    assert count_booked_cruises(db, DEFAULT_AGENCY_ID) == 2
    assert sum_booked_cruise_volume(db, DEFAULT_AGENCY_ID) == 9000.0

    aggregates = get_booked_cruise_aggregates(db, DEFAULT_AGENCY_ID)
    assert aggregates.booking_count == 2
    assert aggregates.total_volume == 9000.0
    assert aggregates.total_commission == 900.0
