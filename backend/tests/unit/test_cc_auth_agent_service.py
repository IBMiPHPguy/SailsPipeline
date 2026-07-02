from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.constants import CC_AUTH_STATUS_COMPLETED, CC_AUTH_STATUS_PENDING, PROPOSED_CRUISE_STATUS_ACCEPTED
from app.models import CreditCardAuthorization, ProposedCruise, TravelRequest
from app.services.cc_auth_agent_service import (
    list_request_cc_authorizations,
    purge_request_cc_authorization,
    reveal_request_cc_authorization,
)
from app.services.cc_auth_service import CCAuthService
from app.tenant_constants import DEFAULT_AGENCY_ID

SAMPLE_CARD_PAYLOAD = {
    "cardholder_name": "Jane Cruise",
    "card_number": "4111111111111111",
    "expiration": "12/30",
    "security_code": "123",
}


def _create_request_with_pending_auth(db, test_user, *, token: str, auth_id: str) -> tuple[TravelRequest, CreditCardAuthorization]:
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
        id=auth_id,
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token=token,
        status=CC_AUTH_STATUS_PENDING,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(record)
    db.commit()
    db.refresh(request)
    db.refresh(record)
    return request, record


def _complete_with_sample_card(db, token: str) -> None:
    asyncio.run(CCAuthService(db).complete_authorization(token, SAMPLE_CARD_PAYLOAD))


def test_list_request_cc_authorizations_reports_vault_flags(db, test_user):
    request, record = _create_request_with_pending_auth(db, test_user, token="list-token", auth_id="auth-list-1")
    _complete_with_sample_card(db, "list-token")

    summaries = list_request_cc_authorizations(db, request_id=request.id)
    assert len(summaries) == 1
    assert summaries[0]["id"] == record.id
    assert summaries[0]["status"] == CC_AUTH_STATUS_COMPLETED
    assert summaries[0]["has_card_data"] is True
    assert summaries[0]["card_data_purged"] is False


def test_reveal_request_cc_authorization_rejects_invalid_vault_key(db, test_user):
    request, record = _create_request_with_pending_auth(db, test_user, token="reveal-bad-key", auth_id="auth-reveal-1")
    _complete_with_sample_card(db, "reveal-bad-key")

    with pytest.raises(HTTPException) as exc:
        reveal_request_cc_authorization(
            db,
            request_id=request.id,
            authorization_id=record.id,
            vault_access_key="not-the-test-key",
        )
    assert exc.value.status_code == 403


def test_reveal_request_cc_authorization_rejects_purged_vault(db, test_user):
    request, record = _create_request_with_pending_auth(db, test_user, token="reveal-purged", auth_id="auth-reveal-2")
    _complete_with_sample_card(db, "reveal-purged")
    purge_request_cc_authorization(db, request_id=request.id, authorization_id=record.id)

    with pytest.raises(HTTPException) as exc:
        reveal_request_cc_authorization(
            db,
            request_id=request.id,
            authorization_id=record.id,
            vault_access_key="test-vault-access-key",
        )
    assert exc.value.status_code == 410


def test_purge_request_cc_authorization_rejects_already_purged(db, test_user):
    request, record = _create_request_with_pending_auth(db, test_user, token="purge-twice", auth_id="auth-purge-2")
    _complete_with_sample_card(db, "purge-twice")
    purge_request_cc_authorization(db, request_id=request.id, authorization_id=record.id)

    with pytest.raises(HTTPException) as exc:
        purge_request_cc_authorization(db, request_id=request.id, authorization_id=record.id)
    assert exc.value.status_code == 400


def test_purge_card_data_rejects_pending_authorization(db, test_user):
    request, record = _create_request_with_pending_auth(db, test_user, token="purge-pending", auth_id="auth-purge-3")

    with pytest.raises(HTTPException) as exc:
        purge_request_cc_authorization(db, request_id=request.id, authorization_id=record.id)
    assert exc.value.status_code == 400


def test_complete_authorization_rejects_invalid_card_payload(db, test_user):
    request, _record = _create_request_with_pending_auth(
        db,
        test_user,
        token="complete-invalid",
        auth_id="auth-complete-invalid",
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            CCAuthService(db).complete_authorization(
                "complete-invalid",
                {**SAMPLE_CARD_PAYLOAD, "card_number": "1234"},
            )
        )
    assert exc.value.status_code == 400

    summaries = list_request_cc_authorizations(db, request_id=request.id)
    assert summaries[0]["status"] == CC_AUTH_STATUS_PENDING
