from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Agency, TravelRequest
from app.services.tc_service import TCService
from app.tenant_context import set_current_agency_id


def _invalid_token_detail(reason: str) -> str:
    return {
        "missing_token": "Terms acceptance token is required.",
        "not_found": "Terms acceptance link was not found.",
        "expired": "This terms acceptance link has expired. Contact your travel advisor for a new link.",
        "invalid_status": "This terms acceptance link has already been used or is no longer active.",
    }.get(reason, "Terms acceptance link is not valid.")


def _invalid_token_status_code(reason: str) -> int:
    if reason == "not_found":
        return 404
    return 410


async def get_terms_portal_context(db: Session, token: str) -> dict:
    tc_service = TCService(db)
    validation = await tc_service.validate_token(token)
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
    terms_text = tc_service.render_terms_for_agency(agency=agency)

    return {
        "valid": True,
        "passenger_name": f"{request.first_name} {request.last_name}".strip(),
        "passenger_email": request.email.strip(),
        "agency_name": agency_name,
        "terms_text": terms_text,
        "expires_at": validation["expires_at"],
        "request_id": validation["request_id"],
    }


async def complete_terms_portal(db: Session, token: str, ip_address: str) -> dict:
    validation = await TCService(db).validate_token(token)
    if validation.get("valid"):
        set_current_agency_id(validation["agency_id"])

    accepted = await TCService(db).record_acceptance(token, ip_address)
    if not accepted:
        raise HTTPException(status_code=500, detail="Unable to record terms acceptance.")

    return {
        "message": "Thank you, your agency profile is up to date!",
        "accepted": True,
    }
