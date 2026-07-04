import pytest

from app.passenger_helpers import (
    activate_passenger_record,
    attach_passenger_to_request,
    create_passenger_record,
    deactivate_passenger_record,
    get_passenger_or_none,
    get_passenger_request_count,
    list_passengers_with_request_counts,
    search_passengers,
)


def _create_passenger(db, *, first_name="Jane", last_name="Cruiser", is_active=True):
    passenger = create_passenger_record(
        db,
        first_name=first_name,
        last_name=last_name,
        email="jane@example.com",
        phone="5551234567",
        date_of_birth=None,
        created_by_id=None,
    )
    passenger.is_active = is_active
    db.flush()
    return passenger


def test_deactivate_passenger_record_sets_inactive(db):
    passenger = _create_passenger(db)

    deactivate_passenger_record(db, passenger)

    assert passenger.is_active is False


def test_activate_passenger_record_sets_active(db):
    passenger = _create_passenger(db, is_active=False)

    activate_passenger_record(db, passenger)

    assert passenger.is_active is True


def test_search_passengers_excludes_inactive_clients(db):
    active = _create_passenger(db, first_name="Active", last_name="Client")
    inactive = _create_passenger(db, first_name="Inactive", last_name="Client", is_active=False)
    db.commit()

    results = search_passengers(db, "Client")

    assert [passenger.id for passenger in results] == [active.id]
    assert inactive.id not in {passenger.id for passenger in results}


def test_search_passengers_includes_reactivated_client(db):
    passenger = _create_passenger(db, first_name="Returning", last_name="Client", is_active=False)
    activate_passenger_record(db, passenger)
    db.commit()

    results = search_passengers(db, "Returning")

    assert [result.id for result in results] == [passenger.id]


def test_attach_passenger_to_request_rejects_inactive_client(db):
    from datetime import date

    from app.models import TravelRequest, User
    from app.security import hash_password

    user = User(
        username="inactive-user",
        email="inactive@example.com",
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
    passenger = _create_passenger(db, is_active=False)
    db.add_all([user, request])
    db.flush()

    with pytest.raises(ValueError, match="Inactive clients cannot be added"):
        attach_passenger_to_request(db, request_id=request.id, passenger_id=passenger.id)


def test_search_passengers_matches_name_email_and_phone(db):
    alpha = _create_passenger(db, first_name="Alpha", last_name="Tester", is_active=True)
    alpha.email = "alpha@example.com"
    alpha.phone = "5551112222"
    beta = _create_passenger(db, first_name="Beta", last_name="Client", is_active=True)
    db.commit()

    assert [item.id for item in search_passengers(db, "Alpha")] == [alpha.id]
    assert [item.id for item in search_passengers(db, "alpha@example.com")] == [alpha.id]
    assert [item.id for item in search_passengers(db, "5551112222")] == [alpha.id]
    assert beta.id not in {item.id for item in search_passengers(db, "Alpha")}


def test_search_passengers_empty_query_returns_recent_active_clients(db):
    first = _create_passenger(db, first_name="First", last_name="Client")
    second = _create_passenger(db, first_name="Second", last_name="Client")
    db.commit()

    results = search_passengers(db, "", limit=10)
    assert {item.id for item in results} == {first.id, second.id}


def test_get_passenger_or_none_and_list_with_request_counts(db):
    passenger = _create_passenger(db)
    db.commit()

    assert get_passenger_or_none(db, passenger.id) is not None
    assert get_passenger_or_none(db, 999999) is None

    rows = list_passengers_with_request_counts(db)
    assert any(row[0].id == passenger.id and row[1] == 0 for row in rows)


def test_get_passenger_request_count(db):
    passenger = _create_passenger(db)
    db.commit()

    assert get_passenger_request_count(db, passenger.id) == 0


def test_attach_passenger_to_request_rejects_missing_passenger(db):
    with pytest.raises(ValueError, match="Passenger not found"):
        attach_passenger_to_request(db, request_id=1, passenger_id=999999)


def test_attach_passenger_to_request_rejects_duplicate_link(db):
    from datetime import date

    from app.models import TravelRequest, User
    from app.security import hash_password

    user = User(
        username="dup-user",
        email="dup@example.com",
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
    passenger = _create_passenger(db)
    db.add_all([user, request])
    db.flush()
    attach_passenger_to_request(db, request.id, passenger.id, is_primary=True)

    with pytest.raises(ValueError, match="already attached"):
        attach_passenger_to_request(db, request.id, passenger.id)


def test_detach_request_passenger_from_proposed_cruises_allows_deletion(db):
    from datetime import date
    from decimal import Decimal

    from app.models import ProposedCruise, ProposedCruisePassenger, RequestPassenger, TravelRequest, User
    from app.proposed_cruise_helpers import default_proposed_cruise_includes_dict
    from app.security import hash_password
    from app.services.passenger_service import detach_request_passenger_from_proposed_cruises

    user = User(
        username="delete-guest-user",
        email="delete-guest@example.com",
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

    primary_passenger = _create_passenger(db, first_name="Jane", last_name="Cruiser")
    guest_passenger = _create_passenger(db, first_name="Mary", last_name="Guest")
    primary = attach_passenger_to_request(db, request.id, primary_passenger.id, is_primary=True)
    guest = attach_passenger_to_request(db, request.id, guest_passenger.id)

    cruise = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean",
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
    cruise.passenger_links.append(ProposedCruisePassenger(request_passenger=guest, cabin_index=0))
    db.commit()

    removed = detach_request_passenger_from_proposed_cruises(
        db,
        request_passenger_id=guest.id,
        request_id=request.id,
    )
    assert removed == 1

    db.delete(guest)
    db.commit()

    remaining = (
        db.query(RequestPassenger)
        .filter(RequestPassenger.travel_request_id == request.id)
        .all()
    )
    assert len(remaining) == 1
    assert remaining[0].id == primary.id
