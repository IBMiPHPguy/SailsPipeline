from datetime import date

from app.models import Passenger, User
from app.passenger_helpers import search_clients_with_request_counts
from app.security import hash_password


def _create_client(db, *, user: User, first_name: str, last_name: str, email: str, phone: str) -> Passenger:
    passenger = Passenger(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        date_of_birth=date(1980, 5, 15),
        created_by_id=user.id,
        is_active=True,
    )
    db.add(passenger)
    db.flush()
    return passenger


def test_search_clients_with_request_counts_filters_by_name(db):
    user = User(username="client-agent", email="client-agent@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()

    _create_client(db, user=user, first_name="Alpha", last_name="Client", email="alpha@example.com", phone="5551112222")
    _create_client(db, user=user, first_name="Beta", last_name="Client", email="beta@example.com", phone="5553334444")
    db.commit()

    rows, total, registry_count = search_clients_with_request_counts(db, query="Alpha")

    assert registry_count == 2
    assert total == 1
    assert len(rows) == 1
    assert rows[0][0].first_name == "Alpha"


def test_search_clients_with_request_counts_matches_phone_and_dob(db):
    user = User(username="client-agent-2", email="client-agent-2@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()

    _create_client(db, user=user, first_name="Gamma", last_name="Traveler", email="gamma@example.com", phone="5559998888")
    db.commit()

    phone_rows, phone_total, _ = search_clients_with_request_counts(db, query="9998888")
    dob_rows, dob_total, _ = search_clients_with_request_counts(db, query="1980-05-15")

    assert phone_total == 1
    assert phone_rows[0][0].first_name == "Gamma"
    assert dob_total == 1
    assert dob_rows[0][0].first_name == "Gamma"


def test_search_clients_with_request_counts_paginates_results(db):
    user = User(username="client-agent-3", email="client-agent-3@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()

    for index in range(3):
        _create_client(
            db,
            user=user,
            first_name=f"Client{index}",
            last_name="Paged",
            email=f"client{index}@example.com",
            phone=f"555000000{index}",
        )
    db.commit()

    page_one, total, registry_count = search_clients_with_request_counts(db, page=1, page_size=2)
    page_two, _, _ = search_clients_with_request_counts(db, page=2, page_size=2)

    assert registry_count == 3
    assert total == 3
    assert len(page_one) == 2
    assert len(page_two) == 1
