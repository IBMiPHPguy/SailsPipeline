from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.cc_auth_email import CC_AUTH_CONTENT_END, CC_AUTH_CONTENT_START, build_cc_auth_email_html
from app.cc_auth_helpers import CcAuthCruiseSummary, build_cc_auth_cruise_summaries, compute_cruise_deposit_due
from app.constants import CC_AUTH_STATUS_COMPLETED, CC_AUTH_STATUS_EXPIRED, CC_AUTH_STATUS_PENDING
from app.services.cc_auth_service import CCAuthService


def _sample_cruise(**overrides):
    base = {
        "id": 1,
        "cabin_pricing": [{"deposit_amount": "250.00", "cost": "2100.00"}],
        "cabin_hold_reservation_ids": None,
        "deposit_amount": Decimal("250.00"),
        "cost": Decimal("2100.00"),
        "departure_date": date(2026, 8, 1),
        "cruise_line": "Royal Caribbean International",
        "ship": "Wonder of the Seas",
        "room_category": "Balcony",
        "final_payment_due_date": date(2026, 6, 1),
        "status": "Accepted",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sample_request(**overrides):
    base = {
        "id": 42,
        "agency_id": "agency-1",
        "cabins_needed": 2,
        "first_name": "Jane",
        "last_name": "Cruise",
        "email": "jane@example.com",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_compute_cruise_deposit_due_sums_all_cabins():
    cruise = _sample_cruise(
        cabin_pricing=[
            {"deposit_amount": "200.00", "cost": "2000.00"},
            {"deposit_amount": "300.00", "cost": "2200.00"},
        ],
    )
    total = compute_cruise_deposit_due(cruise, cabins_needed=2)
    assert total == Decimal("500.00")


def test_compute_cruise_deposit_due_multiplies_by_reservation_count():
    cruise = _sample_cruise(
        cabin_pricing=[{"deposit_amount": "250.00", "cost": "2100.00"}],
        cabin_hold_reservation_ids=[["RES-1", "RES-2"]],
    )
    total = compute_cruise_deposit_due(cruise, cabins_needed=1)
    assert total == Decimal("500.00")


def test_build_cc_auth_cruise_summaries_for_back_to_back():
    request = _sample_request(cabins_needed=1)
    cruises = [
        _sample_cruise(
            id=1,
            deposit_amount=Decimal("300.00"),
            cost=Decimal("3000.00"),
            cabin_pricing=[{"deposit_amount": "300.00", "cost": "3000.00"}],
        ),
        _sample_cruise(
            id=2,
            departure_date=date(2026, 8, 15),
            ship="Symphony of the Seas",
            deposit_amount=Decimal("400.00"),
            cost=Decimal("4000.00"),
            cabin_pricing=[{"deposit_amount": "400.00", "cost": "4000.00"}],
        ),
    ]
    summaries, total = build_cc_auth_cruise_summaries(request, cruises)
    assert len(summaries) == 2
    assert total == Decimal("700.00")
    assert summaries[0].ship == "Wonder of the Seas"
    assert summaries[1].ship == "Symphony of the Seas"


def test_build_cc_auth_email_html_includes_cta_and_security_notice():
    html = build_cc_auth_email_html(
        passenger_name="Jane Cruise",
        agency_name="Cruise Seakers Travel LLC",
        cruises=[
            CcAuthCruiseSummary(
                cruise_line="Royal Caribbean International",
                ship="Wonder of the Seas",
                sailing_date=date(2026, 8, 1),
                cabin_type="Balcony",
                deposit_amount=Decimal("500.00"),
                final_payment_due_date=date(2026, 6, 1),
            )
        ],
        total_deposit_due=Decimal("500.00"),
        portal_url="https://portal.example/cc-auth/abc123",
        primary_color="#0d5c75",
    )
    assert CC_AUTH_CONTENT_START in html
    assert CC_AUTH_CONTENT_END in html
    assert "Jane Cruise" in html
    assert "Securely Authorize Card" in html
    assert "https://portal.example/cc-auth/abc123" in html
    assert "expire in 48 hours" in html
    assert "$500.00" in html


def test_create_auth_request_persists_token_and_returns_portal_url(db, test_user, monkeypatch):
    from app.models import TravelRequest
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    monkeypatch.setattr("app.services.cc_auth_service.settings.cc_auth_portal_base_url", "http://localhost:5173/cc-auth")

    service = CCAuthService(db)
    portal_url = asyncio.run(service.create_auth_request(request.id))

    assert portal_url.startswith("http://localhost:5173/cc-auth/")
    token = portal_url.rsplit("/", 1)[-1]
    assert len(token) >= 32

    validation = asyncio.run(service.validate_token(token))
    assert validation["valid"] is True
    assert validation["travel_request_id"] == request.id


def test_validate_token_rejects_expired(db, test_user):
    from app.models import CreditCardAuthorization, TravelRequest
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()

    record = CreditCardAuthorization(
        id="auth-1",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token="expired-token-value",
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    db.add(record)
    db.commit()

    service = CCAuthService(db)
    result = asyncio.run(service.validate_token("expired-token-value"))
    assert result["valid"] is False
    assert result["reason"] == "expired"
    assert "travel_request_id" not in result

    db.refresh(record)
    assert record.status == CC_AUTH_STATUS_EXPIRED


SAMPLE_CARD_PAYLOAD = {
    "cardholder_name": "Jane Cruise",
    "card_number": "4111111111111111",
    "expiration": "12/30",
    "security_code": "123",
}


def test_complete_authorization_marks_record_completed(db, test_user):
    from app.constants import CC_AUTH_STATUS_COMPLETED
    from app.models import CreditCardAuthorization, TravelRequest
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()

    record = CreditCardAuthorization(
        id="auth-complete-1",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token="complete-me-token",
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(record)
    db.commit()

    service = CCAuthService(db)
    result = asyncio.run(service.complete_authorization("complete-me-token", SAMPLE_CARD_PAYLOAD))
    assert result["status"] == CC_AUTH_STATUS_COMPLETED
    assert result["completed_at"] is not None

    db.refresh(record)
    assert record.status == CC_AUTH_STATUS_COMPLETED
    assert record.completed_at is not None
    assert record.encrypted_card_data
    assert "4111111111111111" not in record.encrypted_card_data


def test_purge_card_data_clears_encrypted_payload(db, test_user):
    from app.services.cc_auth_agent_service import purge_request_cc_authorization, reveal_request_cc_authorization

    from app.models import CreditCardAuthorization, TravelRequest
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()

    record = CreditCardAuthorization(
        id="auth-purge-1",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token="purge-me-token",
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(record)
    db.commit()

    service = CCAuthService(db)
    asyncio.run(service.complete_authorization("purge-me-token", SAMPLE_CARD_PAYLOAD))
    db.refresh(record)

    revealed = reveal_request_cc_authorization(
        db,
        request_id=request.id,
        authorization_id=record.id,
        vault_access_key="test-vault-access-key",
    )
    assert revealed["card"]["card_number"] == "4111111111111111"

    purge_result = purge_request_cc_authorization(db, request_id=request.id, authorization_id=record.id)
    assert purge_result["card_data_purged"] is True
    db.refresh(record)
    assert record.encrypted_card_data is None
    assert record.status == CC_AUTH_STATUS_COMPLETED


def test_get_cc_auth_portal_context_returns_cruise_summary(db, test_user):
    from app.constants import PROPOSED_CRUISE_STATUS_ACCEPTED
    from app.models import CreditCardAuthorization, ProposedCruise, TravelRequest
    from app.services.cc_auth_portal_service import get_cc_auth_portal_context
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()

    cruise = ProposedCruise(
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        departure_date=date(2026, 9, 15),
        cruise_line="Princess Cruises",
        ship="Sky Princess",
        number_of_nights=7,
        itinerary_name="Eastern Caribbean",
        room_category="Balcony",
        room_number="B210",
        passengers_in_room=2,
        deposit_amount=Decimal("500.00"),
        deposit_due_date=date(2026, 6, 1),
        final_payment_due_date=date(2026, 8, 1),
        cost=Decimal("4200.00"),
        status=PROPOSED_CRUISE_STATUS_ACCEPTED,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    record = CreditCardAuthorization(
        id="auth-portal-1",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token="portal-token-value",
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add_all([cruise, record])
    db.commit()

    payload = asyncio.run(get_cc_auth_portal_context(db, "portal-token-value"))
    assert payload["valid"] is True
    assert payload["passenger_name"] == "Jane Cruise"
    assert payload["total_deposit_due"] == "500.00"
    assert len(payload["cruises"]) == 1
    assert payload["cruises"][0]["ship"] == "Sky Princess"


def test_get_cc_auth_portal_context_rejects_when_no_accepted_cruise(db, test_user):
    from fastapi import HTTPException

    from app.models import CreditCardAuthorization, TravelRequest
    from app.services.cc_auth_portal_service import get_cc_auth_portal_context
    from app.tenant_constants import DEFAULT_AGENCY_ID

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email="jane@example.com",
        phone="555-0100",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()
    record = CreditCardAuthorization(
        id="auth-portal-missing-cruise",
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token="portal-missing-cruise",
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(record)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_cc_auth_portal_context(db, "portal-missing-cruise"))
    assert exc.value.status_code == 409
