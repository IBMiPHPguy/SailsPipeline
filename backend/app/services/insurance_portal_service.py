from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.insurance_waiver import render_insurance_waiver_text
from app.models import Agency, TravelRequest
from app.services.insurance_service import InsuranceService
from app.tenant_context import set_current_agency_id


def _invalid_token_detail(reason: str) -> str:
    return {
        "missing_token": "Insurance waiver token is required.",
        "not_found": "Insurance waiver link was not found.",
        "expired": "This insurance waiver link has expired. Contact your travel advisor for a new link.",
        "invalid_status": "This insurance waiver link has already been used or is no longer active.",
    }.get(reason, "Insurance waiver link is not valid.")


def _invalid_token_status_code(reason: str) -> int:
    if reason == "not_found":
        return 404
    return 410


async def get_insurance_waiver_portal_context(db: Session, token: str) -> dict:
    insurance_service = InsuranceService(db)
    validation = await insurance_service.validate_token(token)
    if not validation.get("valid"):
        reason = validation.get("reason", "invalid_token")
        raise HTTPException(
            status_code=_invalid_token_status_code(reason),
            detail=_invalid_token_detail(reason),
        )

    agency_id = validation["agency_id"]
    travel_request_id = validation["travel_request_id"]
    set_current_agency_id(agency_id)

    request = db.get(TravelRequest, travel_request_id)
    if request is None or request.agency_id != agency_id:
        raise HTTPException(status_code=404, detail="Travel request not found.")

    agency = db.get(Agency, agency_id)
    agency_name = agency.name if agency else "Your travel agency"
    passenger_name = f"{request.first_name} {request.last_name}".strip()
    waiver_text = render_insurance_waiver_text(agency_name=agency_name, passenger_name=passenger_name)

    return {
        "valid": True,
        "passenger_name": passenger_name,
        "passenger_email": request.email.strip(),
        "agency_name": agency_name,
        "waiver_text": waiver_text,
        "expires_at": validation["expires_at"],
        "request_id": travel_request_id,
    }


async def complete_insurance_waiver_portal(db: Session, token: str, ip_address: str) -> dict:
    signed = await InsuranceService(db).record_waiver_signature(token, ip_address)
    if not signed:
        raise HTTPException(status_code=500, detail="Unable to record insurance waiver signature.")

    return {
        "message": "Thank you. Your insurance waiver has been recorded.",
        "signed": True,
    }
