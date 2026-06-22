from datetime import UTC, date, datetime
from decimal import Decimal

from app.constants import (
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_OPEN,
)
from app.models import ProposedCruise, TravelRequest, User
from app.security import hash_password
from app.services.request_service import ACTIVE_PIPELINE_QUOTE_STATUSES, calculate_open_pipeline_value


def _create_user(db, *, username: str) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()
    return user


def _create_open_request(db, *, user: User, first_name: str, last_name: str, email: str) -> TravelRequest:
    request = TravelRequest(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        close_reason=None,
        created_by=user,
        updated_by=user,
        updated_at=datetime.now(UTC),
    )
    db.add(request)
    db.flush()
    return request


def _create_proposed_cruise(
    db,
    *,
    request: TravelRequest,
    user: User,
    cost: Decimal,
    status: str,
) -> ProposedCruise:
    cruise = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 8, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western Caribbean",
        room_category="Balcony",
        room_number="",
        passengers_in_room=2,
        deposit_amount=Decimal("500.00"),
        deposit_due_date=date(2026, 6, 1),
        final_payment_due_date=date(2026, 7, 1),
        cost=cost,
        includes={},
        status=status,
        created_by=user,
        updated_by=user,
    )
    db.add(cruise)
    db.flush()
    return cruise


def test_calculate_open_pipeline_value_uses_highest_quote_per_request(db):
    user = _create_user(db, username="pipeline-agent")
    request_one = _create_open_request(db, user=user, first_name="Jane", last_name="Cruiser", email="jane@example.com")
    request_two = _create_open_request(db, user=user, first_name="John", last_name="Cruiser", email="john@example.com")

    _create_proposed_cruise(
        db,
        request=request_one,
        user=user,
        cost=Decimal("4200.00"),
        status=PROPOSED_CRUISE_STATUS_PROPOSED,
    )
    _create_proposed_cruise(
        db,
        request=request_one,
        user=user,
        cost=Decimal("6800.00"),
        status=PROPOSED_CRUISE_STATUS_PROPOSED,
    )
    _create_proposed_cruise(
        db,
        request=request_two,
        user=user,
        cost=Decimal("7700.00"),
        status=PROPOSED_CRUISE_STATUS_ACCEPTED,
    )
    _create_proposed_cruise(
        db,
        request=request_two,
        user=user,
        cost=Decimal("3900.00"),
        status=PROPOSED_CRUISE_STATUS_REJECTED,
    )
    db.commit()

    assert calculate_open_pipeline_value(db) == 14500.0
    assert PROPOSED_CRUISE_STATUS_REJECTED not in ACTIVE_PIPELINE_QUOTE_STATUSES


def test_calculate_open_pipeline_value_sums_back_to_back_accepted_cruises(db):
    user = _create_user(db, username="pipeline-b2b-agent")
    request = _create_open_request(
        db,
        user=user,
        first_name="Multi",
        last_name="Cruise",
        email="multi@example.com",
    )

    _create_proposed_cruise(
        db,
        request=request,
        user=user,
        cost=Decimal("5000.00"),
        status=PROPOSED_CRUISE_STATUS_ACCEPTED,
    )
    _create_proposed_cruise(
        db,
        request=request,
        user=user,
        cost=Decimal("4000.00"),
        status=PROPOSED_CRUISE_STATUS_ACCEPTED,
    )
    db.commit()

    assert calculate_open_pipeline_value(db) == 9000.0
