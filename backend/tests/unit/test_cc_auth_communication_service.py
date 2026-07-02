from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.constants import PROPOSED_CRUISE_STATUS_ACCEPTED, PROPOSED_CRUISE_STATUS_PROPOSED
from app.models import CreditCardAuthorization, ProposedCruise, TravelRequest
from app.services.cc_auth_communication_service import send_cc_auth_email
from app.tenant_constants import DEFAULT_AGENCY_ID


def _seed_request_with_cruise(
    db,
    test_user,
    *,
    email: str = "jane@example.com",
    deposit_amount: Decimal = Decimal("500.00"),
    cruise_status: str = PROPOSED_CRUISE_STATUS_ACCEPTED,
) -> TravelRequest:
    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Jane",
        last_name="Cruise",
        email=email,
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
        deposit_amount=deposit_amount,
        deposit_due_date=date(2026, 6, 1),
        final_payment_due_date=date(2026, 8, 1),
        cost=Decimal("4200.00"),
        status=cruise_status,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(cruise)
    db.commit()
    db.refresh(request)
    return request


def test_send_cc_auth_email_rejects_missing_client_email(db, test_user):
    request = _seed_request_with_cruise(db, test_user, email="   ")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(send_cc_auth_email(db, request=request, current_user=test_user))
    assert exc.value.status_code == 400
    assert "email" in exc.value.detail.lower()


def test_send_cc_auth_email_rejects_without_accepted_cruise(db, test_user):
    request = _seed_request_with_cruise(db, test_user, cruise_status=PROPOSED_CRUISE_STATUS_PROPOSED)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(send_cc_auth_email(db, request=request, current_user=test_user))
    assert exc.value.status_code == 400
    assert "accepted cruise" in exc.value.detail.lower()


def test_send_cc_auth_email_rejects_zero_deposit(db, test_user):
    request = _seed_request_with_cruise(db, test_user, deposit_amount=Decimal("0.00"))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(send_cc_auth_email(db, request=request, current_user=test_user))
    assert exc.value.status_code == 400
    assert "deposit" in exc.value.detail.lower()


def test_send_cc_auth_email_creates_auth_and_delivers_email(db, test_user, monkeypatch):
    request = _seed_request_with_cruise(db, test_user)
    monkeypatch.setattr(
        "app.services.cc_auth_service.settings.cc_auth_portal_base_url",
        "http://localhost:5173/cc-auth",
    )

    with patch(
        "app.services.cc_auth_communication_service.EmailDeliveryService.send_transactional_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as send_email:
        result = asyncio.run(send_cc_auth_email(db, request=request, current_user=test_user))

    assert result["email_sent"] is True
    assert result["recipient"] == "jane@example.com"
    assert result["accepted_cruise_count"] == 1
    assert result["total_deposit_due"] == "500.00"
    assert str(result["portal_url"]).startswith("http://localhost:5173/cc-auth/")

    send_email.assert_awaited_once()
    kwargs = send_email.await_args.kwargs
    assert kwargs["recipient"] == "jane@example.com"
    assert kwargs["email_type"] == "cc_authorization"
    assert kwargs["travel_request_id"] == str(request.id)

    auth_record = (
        db.query(CreditCardAuthorization)
        .filter(CreditCardAuthorization.travel_request_id == request.id)
        .one()
    )
    assert auth_record.status == "pending"
    assert auth_record.secure_token


def test_send_cc_auth_email_raises_when_delivery_fails(db, test_user, monkeypatch):
    request = _seed_request_with_cruise(db, test_user)
    monkeypatch.setattr(
        "app.services.cc_auth_service.settings.cc_auth_portal_base_url",
        "http://localhost:5173/cc-auth",
    )

    with patch(
        "app.services.cc_auth_communication_service.EmailDeliveryService.send_transactional_email",
        new_callable=AsyncMock,
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(send_cc_auth_email(db, request=request, current_user=test_user))
    assert exc.value.status_code == 502
