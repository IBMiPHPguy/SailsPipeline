from datetime import datetime

import asyncio

from app.constants import INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED, INSURANCE_WAIVER_REQUEST_STATUS_PENDING
from app.models import InsuranceWaiverRequest, TravelRequest, User
from app.security import hash_password
from app.services.insurance_service import InsuranceService


def _seed_open_request(db) -> TravelRequest:
    user = User(
        username="insurance-agent",
        email="agent@example.com",
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
        departure_date=datetime(2026, 6, 1).date(),
        return_date=datetime(2026, 6, 8).date(),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status="Open",
        created_by=user,
        updated_by=user,
    )
    db.add_all([user, request])
    db.commit()
    db.refresh(request)
    return request


def test_create_waiver_request_resend_expires_previous_active_link(db):
    request = _seed_open_request(db)
    service = InsuranceService(db)

    first_url, first_resent = asyncio.run(service.create_waiver_request(request.id))
    assert first_resent is False

    first_record = (
        db.query(InsuranceWaiverRequest)
        .filter(InsuranceWaiverRequest.travel_request_id == request.id)
        .order_by(InsuranceWaiverRequest.created_at.asc())
        .first()
    )
    assert first_record is not None
    assert first_record.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING
    first_token = first_record.secure_token

    second_url, second_resent = asyncio.run(service.create_waiver_request(request.id))
    assert second_resent is True
    assert second_url != first_url

    db.refresh(first_record)
    assert first_record.status == INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED

    active_pending = (
        db.query(InsuranceWaiverRequest)
        .filter(
            InsuranceWaiverRequest.travel_request_id == request.id,
            InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
        )
        .all()
    )
    assert len(active_pending) == 1
    assert active_pending[0].secure_token != first_token

    validation = asyncio.run(service.validate_token(first_token))
    assert validation["valid"] is False
    assert validation["reason"] == "invalid_status"

    validation = asyncio.run(service.validate_token(active_pending[0].secure_token))
    assert validation["valid"] is True
