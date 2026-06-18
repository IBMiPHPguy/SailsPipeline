import pytest

from app.passenger_helpers import (
    activate_passenger_record,
    attach_passenger_to_request,
    create_passenger_record,
    deactivate_passenger_record,
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
    passenger = _create_passenger(db, is_active=False)
    db.commit()

    with pytest.raises(ValueError, match="Inactive clients cannot be added"):
        attach_passenger_to_request(db, request_id=1, passenger_id=passenger.id)
