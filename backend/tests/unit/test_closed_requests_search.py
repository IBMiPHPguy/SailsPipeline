from datetime import UTC, date, datetime, timedelta

import pytest

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED
from app.models import TravelRequest, User
from app.security import hash_password
from app.services.request_service import (
    CLOSED_REQUESTS_PAGE_SIZE_DEFAULT,
    closed_requests_total_pages,
    search_closed_requests,
)


def _create_user(db, *, username: str, email: str) -> User:
    user = User(username=username, email=email, password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()
    return user


def _create_closed_request(
    db,
    *,
    user: User,
    first_name: str,
    last_name: str,
    email: str,
    destination: str,
    close_reason: str,
    cruise_lines: list[str] | None = None,
    updated_at: datetime | None = None,
) -> TravelRequest:
    request = TravelRequest(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone="5551234567",
        cruise_lines=cruise_lines or ["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination=destination,
        destination_details=None,
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason=close_reason,
        created_by=user,
        updated_by=user,
        updated_at=updated_at or datetime.now(UTC),
    )
    db.add(request)
    db.flush()
    return request


def test_search_closed_requests_filters_by_client_name(db):
    agent = _create_user(db, username="agent1", email="agent1@example.com")
    _create_closed_request(
        db,
        user=agent,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@example.com",
        destination="Caribbean",
        close_reason="Client declined",
    )
    _create_closed_request(
        db,
        user=agent,
        first_name="John",
        last_name="Sailor",
        email="john@example.com",
        destination="Alaska",
        close_reason="No suitable options",
    )
    db.commit()

    items, total = search_closed_requests(db, query="Jane")

    assert total == 1
    assert len(items) == 1
    assert items[0].first_name == "Jane"


def test_search_closed_requests_matches_close_reason_and_destination(db):
    agent = _create_user(db, username="agent2", email="agent2@example.com")
    _create_closed_request(
        db,
        user=agent,
        first_name="Amy",
        last_name="Wave",
        email="amy@example.com",
        destination="Europe",
        close_reason=PRIMARY_CLOSE_REASON,
    )
    _create_closed_request(
        db,
        user=agent,
        first_name="Bob",
        last_name="Wave",
        email="bob@example.com",
        destination="Caribbean",
        close_reason="Client declined",
    )
    db.commit()

    purchased_items, purchased_total = search_closed_requests(db, query="Purchased")
    destination_items, destination_total = search_closed_requests(db, query="Europe")

    assert purchased_total == 1
    assert purchased_items[0].close_reason == PRIMARY_CLOSE_REASON
    assert destination_total == 1
    assert destination_items[0].destination == "Europe"


def test_search_closed_requests_paginates_results(db):
    agent = _create_user(db, username="agent3", email="agent3@example.com")
    base_time = datetime(2026, 6, 10, 12, 0, tzinfo=UTC)
    for index in range(3):
        _create_closed_request(
            db,
            user=agent,
            first_name=f"Client{index}",
            last_name="Closed",
            email=f"client{index}@example.com",
            destination="Caribbean",
            close_reason="Client declined",
            updated_at=base_time - timedelta(days=index),
        )
    db.commit()

    page_one, total = search_closed_requests(db, page=1, page_size=2)
    page_two, _ = search_closed_requests(db, page=2, page_size=2)

    assert total == 3
    assert len(page_one) == 2
    assert len(page_two) == 1
    assert page_one[0].first_name == "Client0"
    assert page_two[0].first_name == "Client2"


@pytest.mark.parametrize(
    ("total", "page_size", "expected_pages"),
    [
        (0, CLOSED_REQUESTS_PAGE_SIZE_DEFAULT, 0),
        (1, 25, 1),
        (25, 25, 1),
        (26, 25, 2),
    ],
)
def test_closed_requests_total_pages(total, page_size, expected_pages):
    assert closed_requests_total_pages(total, page_size) == expected_pages
