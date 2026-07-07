from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.constants import PROPOSED_CRUISE_STATUS_ACCEPTED
from app.models import CreditCardAuthorization, ProposedCruise, TravelRequest
from app.tenant_constants import DEFAULT_AGENCY_ID

SAMPLE_CARD_PAYLOAD = {
    "cardholder_name": "Jane Cruise",
    "card_number": "4111111111111111",
    "expiration": "12/30",
    "security_code": "123",
}


def _seed_open_request_with_accepted_cruise(db, test_user) -> tuple[TravelRequest, str]:
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
    db.add(cruise)
    db.commit()
    db.refresh(request)
    return request, "route-test-token"


def _create_pending_auth(db, request: TravelRequest, token: str, auth_id: str) -> CreditCardAuthorization:
    record = CreditCardAuthorization(
        id=auth_id,
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=request.id,
        secure_token=token,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def test_public_validate_and_complete_routes(client, db, test_user):
    request, token = _seed_open_request_with_accepted_cruise(db, test_user)
    _create_pending_auth(db, request, token, "route-auth-1")

    validate_response = client.get(f"/api/cc-auth/validate/{token}")
    assert validate_response.status_code == 200, validate_response.text
    body = validate_response.json()
    assert body["passenger_name"] == "Jane Cruise"
    assert body["total_deposit_due"] == "500.00"
    assert body["branding"]["agency_name"]

    complete_response = client.post(f"/api/cc-auth/complete/{token}", json=SAMPLE_CARD_PAYLOAD)
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["status"] == "completed"


def test_public_validate_route_hides_internal_ids_for_expired_token(client, db, test_user):
    request, _token = _seed_open_request_with_accepted_cruise(db, test_user)
    expired_token = "expired-route-token"
    _create_pending_auth(db, request, expired_token, "route-auth-expired")
    record = (
        db.query(CreditCardAuthorization)
        .filter(CreditCardAuthorization.secure_token == expired_token)
        .one()
    )
    record.expires_at = datetime.utcnow() - timedelta(hours=1)
    db.commit()

    response = client.get(f"/api/cc-auth/validate/{expired_token}")
    assert response.status_code == 410, response.text
    body = response.json()
    assert "travel_request_id" not in body
    assert body["detail"]


def test_public_complete_route_requires_card_payload(client, db, test_user):
    request, token = _seed_open_request_with_accepted_cruise(db, test_user)
    _create_pending_auth(db, request, token, "route-auth-2")

    response = client.post(f"/api/cc-auth/complete/{token}", json={})
    assert response.status_code == 422


def test_agent_list_reveal_and_purge_routes(client, db, test_user, auth_headers):
    from app.services.cc_auth_service import CCAuthService

    request, token = _seed_open_request_with_accepted_cruise(db, test_user)
    record = _create_pending_auth(db, request, token, "route-auth-3")
    asyncio.run(CCAuthService(db).complete_authorization(token, SAMPLE_CARD_PAYLOAD))

    list_response = client.get(f"/api/requests/{request.id}/cc-auth", headers=auth_headers)
    assert list_response.status_code == 200, list_response.text
    summaries = list_response.json()
    assert len(summaries) == 1
    assert summaries[0]["has_card_data"] is True

    bad_reveal = client.post(
        f"/api/requests/{request.id}/cc-auth/{record.id}/reveal",
        headers=auth_headers,
        json={"vault_access_key": "wrong-key"},
    )
    assert bad_reveal.status_code == 403

    reveal_response = client.post(
        f"/api/requests/{request.id}/cc-auth/{record.id}/reveal",
        headers=auth_headers,
        json={"vault_access_key": "test-vault-access-key"},
    )
    assert reveal_response.status_code == 200, reveal_response.text
    assert reveal_response.json()["card"]["card_number"] == "4111111111111111"

    purge_response = client.post(
        f"/api/requests/{request.id}/cc-auth/{record.id}/purge",
        headers=auth_headers,
    )
    assert purge_response.status_code == 200, purge_response.text
    assert purge_response.json()["card_data_purged"] is True

    list_after_purge = client.get(f"/api/requests/{request.id}/cc-auth", headers=auth_headers)
    assert list_after_purge.json()[0]["card_data_purged"] is True


def test_agent_routes_require_authentication(client, db, test_user):
    request, token = _seed_open_request_with_accepted_cruise(db, test_user)
    record = _create_pending_auth(db, request, token, "route-auth-4")

    list_response = client.get(f"/api/requests/{request.id}/cc-auth")
    assert list_response.status_code == 401

    reveal_response = client.post(
        f"/api/requests/{request.id}/cc-auth/{record.id}/reveal",
        json={"vault_access_key": "test-vault-access-key"},
    )
    assert reveal_response.status_code == 401


def test_send_cc_auth_email_route(client, db, test_user, auth_headers, monkeypatch):
    request, _token = _seed_open_request_with_accepted_cruise(db, test_user)
    monkeypatch.setattr(
        "app.services.cc_auth_service.settings.cc_auth_portal_base_url",
        "http://localhost:5173/cc-auth",
    )

    with patch(
        "app.services.cc_auth_communication_service.EmailDeliveryService.send_transactional_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = client.post(
            "/api/cc-auth/send",
            headers=auth_headers,
            json={"travel_request_id": request.id},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email_sent"] is True
    assert body["recipient"] == "jane@example.com"
    assert body["accepted_cruise_count"] == 1
    assert body["portal_url"].startswith("http://localhost:5173/cc-auth/")


def test_send_cc_auth_email_route_requires_authentication(client, db, test_user):
    request, _token = _seed_open_request_with_accepted_cruise(db, test_user)

    response = client.post("/api/cc-auth/send", json={"travel_request_id": request.id})
    assert response.status_code == 401
