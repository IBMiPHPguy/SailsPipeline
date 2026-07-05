from datetime import date
from decimal import Decimal

from app.models import ProposedCruise, ProposedCruisePassenger, TravelRequest, User
from app.passenger_helpers import attach_passenger_to_request, create_passenger_record
from app.proposed_cruise_helpers import (
    cabin_rooms_from_cruise,
    default_proposed_cruise_includes_dict,
    normalize_room_passenger_ids,
    passengers_in_room_limits_for_cruise,
    serialize_includes_for_storage,
    sync_cruise_from_cabin_rooms,
    sync_cruise_totals_from_cabin_pricing,
)
from app.security import hash_password
from app.services.proposed_cruise_service import build_room_passengers_from_links, proposed_cruise_to_read


def test_serialize_includes_for_storage_stringifies_credit_amounts():
    payload = serialize_includes_for_storage(
        {
            "drink_package": {"included": False, "name": ""},
            "wifi": {"included": False, "name": ""},
            "tips": False,
            "excursion": False,
            "excursion_credit": {"included": True, "amount": Decimal("50.00")},
            "onboard_credit": {"included": False, "amount": None},
            "gift_obc": {"included": False, "amount": None},
        }
    )

    assert payload["excursion_credit"]["amount"] == "50.00"


def test_sync_cruise_totals_and_from_cabin_rooms():
    cruise = ProposedCruise(
        travel_request_id=1,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("0"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("0"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
    )
    rooms = [
        {
            "room_category": "Balcony",
            "room_number": "1001",
            "passengers_in_room": 2,
            "deposit_amount": "250.00",
            "commission": "0",
            "cost": "4200.00",
            "includes": default_proposed_cruise_includes_dict(),
        }
    ]

    sync_cruise_from_cabin_rooms(cruise, rooms)

    assert cruise.deposit_amount == Decimal("250.00")
    assert cruise.cost == Decimal("4200.00")
    assert cruise.room_category == "Balcony"
    assert cruise.cabin_pricing == [{"deposit_amount": "250.00", "cost": "4200.00"}]

    cruise.cabin_pricing = [{"deposit_amount": "100.00", "cost": "1000.00"}]
    sync_cruise_totals_from_cabin_pricing(cruise)
    assert cruise.deposit_amount == Decimal("100.00")
    assert cruise.cost == Decimal("1000.00")


def test_passengers_in_room_limits_and_room_passenger_normalization():
    cruise = ProposedCruise(
        travel_request_id=1,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("100"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("1000"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
        cabin_rooms=[
            {
                "room_category": "Suite",
                "room_number": "9001",
                "passengers_in_room": 3,
                "deposit_amount": "100",
                "cost": "1000",
                "includes": {},
            },
            {
                "room_category": "Balcony",
                "room_number": "1002",
                "passengers_in_room": 2,
                "deposit_amount": "100",
                "cost": "1000",
                "includes": {},
            },
        ],
    )

    assert passengers_in_room_limits_for_cruise(cruise, 2) == [3, 2]
    assert normalize_room_passenger_ids([[1, 2], [3]], None, 2) == [[1, 2], [3]]


def test_sync_cruise_totals_from_cabin_pricing_skips_empty_or_invalid():
    cruise = ProposedCruise(
        travel_request_id=1,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("100"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("1000"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
    )
    original_deposit = cruise.deposit_amount
    sync_cruise_totals_from_cabin_pricing(cruise)
    assert cruise.deposit_amount == original_deposit

    cruise.cabin_pricing = [{"deposit_amount": "100", "cost": "1000"}, "invalid"]
    sync_cruise_totals_from_cabin_pricing(cruise)
    assert cruise.deposit_amount == Decimal("100")
    assert cruise.cost == Decimal("1000")


def test_passengers_in_room_limits_fills_short_cabin_rooms_list():
    cruise = ProposedCruise(
        travel_request_id=1,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("100"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("1000"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
        cabin_rooms=[{"passengers_in_room": 3}],
    )

    assert passengers_in_room_limits_for_cruise(cruise, 3) == [3, 2, 2]


def test_proposed_cruise_to_read_groups_room_passengers(db):
    user = User(
        username="cruise-user",
        email="cruise@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    request = TravelRequest(
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=2,
        status="Open",
        created_by=user,
        updated_by=user,
    )
    db.add_all([user, request])
    db.flush()

    primary_passenger = create_passenger_record(
        db,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        date_of_birth=None,
        created_by_id=user.id,
    )
    guest_passenger = create_passenger_record(
        db,
        first_name="Bob",
        last_name="Guest",
        email="bob@example.com",
        phone="5550000002",
        date_of_birth=None,
        created_by_id=user.id,
    )
    primary = attach_passenger_to_request(db, request.id, primary_passenger.id, is_primary=True)
    guest = attach_passenger_to_request(db, request.id, guest_passenger.id)
    db.flush()

    cruise = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("250.00"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("4200.00"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(cruise)
    db.flush()
    cruise.passenger_links.extend(
        [
            ProposedCruisePassenger(request_passenger=primary, cabin_index=0),
            ProposedCruisePassenger(request_passenger=guest, cabin_index=1),
        ]
    )
    db.commit()
    db.refresh(cruise)

    room_passengers = build_room_passengers_from_links(cruise, request.cabins_needed)
    assert len(room_passengers) == 2
    assert room_passengers[0][0].first_name == "Jane"
    assert room_passengers[1][0].first_name == "Bob"

    read_model = proposed_cruise_to_read(cruise, request.cabins_needed)
    assert len(read_model.room_passengers) == 2
    assert len(read_model.cabin_rooms) == 2
    assert len(read_model.passengers) == 2
    assert cabin_rooms_from_cruise(cruise, request.cabins_needed)[0].room_category == "Balcony"


def test_build_room_passengers_skips_out_of_range_cabin_index(db):
    user = User(
        username="range-user",
        email="range@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    request = TravelRequest(
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status="Open",
        created_by=user,
        updated_by=user,
    )
    db.add_all([user, request])
    db.flush()

    in_range_passenger = create_passenger_record(
        db,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        date_of_birth=None,
        created_by_id=user.id,
    )
    out_of_range_passenger = create_passenger_record(
        db,
        first_name="Bob",
        last_name="Guest",
        email="bob@example.com",
        phone="5550000002",
        date_of_birth=None,
        created_by_id=user.id,
    )
    in_range = attach_passenger_to_request(db, request.id, in_range_passenger.id, is_primary=True)
    out_of_range = attach_passenger_to_request(db, request.id, out_of_range_passenger.id)
    cruise = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("250.00"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("4200.00"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(cruise)
    db.flush()
    cruise.passenger_links.extend(
        [
            ProposedCruisePassenger(request_passenger=in_range, cabin_index=0),
            ProposedCruisePassenger(request_passenger=out_of_range, cabin_index=5),
        ]
    )
    db.commit()
    db.refresh(cruise)

    rooms = build_room_passengers_from_links(cruise, 1)
    assert len(rooms) == 1
    assert len(rooms[0]) == 1
    assert rooms[0][0].first_name == "Jane"


def test_passengers_in_room_limits_without_cabin_rooms():
    cruise = ProposedCruise(
        travel_request_id=1,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="TBD",
        passengers_in_room=2,
        deposit_amount=Decimal("100"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("1000"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
    )

    assert passengers_in_room_limits_for_cruise(cruise, 3) == [2, 2, 2]


def test_update_proposed_cruise_resyncs_room_passengers_without_duplicate_key_error(db):
    from app.schemas import ProposedCruiseUpdate
    from app.services.proposed_cruise_record_service import update_proposed_cruise

    user = User(
        username="update-cruise-user",
        email="update-cruise@example.com",
        password_hash=hash_password("ValidPass1!"),
    )
    request = TravelRequest(
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status="Open",
        created_by=user,
        updated_by=user,
    )
    db.add_all([user, request])
    db.flush()

    primary_passenger = create_passenger_record(
        db,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        phone="5551234567",
        date_of_birth=None,
        created_by_id=user.id,
    )
    guest_passenger = create_passenger_record(
        db,
        first_name="Bob",
        last_name="Guest",
        email="bob@example.com",
        phone="5550000002",
        date_of_birth=None,
        created_by_id=user.id,
    )
    primary = attach_passenger_to_request(db, request.id, primary_passenger.id, is_primary=True)
    guest = attach_passenger_to_request(db, request.id, guest_passenger.id)
    db.flush()

    cruise = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean International",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Western",
        room_category="Balcony",
        room_number="GTY",
        passengers_in_room=2,
        deposit_amount=Decimal("250.00"),
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=Decimal("4200.00"),
        includes=default_proposed_cruise_includes_dict(),
        status="Proposed",
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(cruise)
    db.flush()
    cruise.passenger_links.extend(
        [
            ProposedCruisePassenger(request_passenger=primary, cabin_index=0),
            ProposedCruisePassenger(request_passenger=guest, cabin_index=0),
        ]
    )
    db.commit()
    db.refresh(cruise)

    payload = ProposedCruiseUpdate.model_validate(
        {
            "room_passenger_ids": [[primary.id, guest.id]],
            "ship": cruise.ship,
        }
    )
    update_proposed_cruise(
        db,
        request_id=request.id,
        cruise_id=cruise.id,
        payload=payload,
        current_user=user,
    )
    update_proposed_cruise(
        db,
        request_id=request.id,
        cruise_id=cruise.id,
        payload=payload,
        current_user=user,
    )

    db.refresh(cruise)
    assert len(cruise.passenger_links) == 2
    assert {link.request_passenger_id for link in cruise.passenger_links} == {primary.id, guest.id}
