from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cc_auth_helpers import build_cc_auth_cruise_summaries
from app.constants import PROPOSED_CRUISE_STATUS_ACCEPTED
from app.models import ProposedCruise, TravelRequest
from app.services.agency_settings_service import build_portal_branding_payload, get_agency_settings_row
from app.services.cc_auth_service import CCAuthService
from app.tenant_context import set_current_agency_id


def _invalid_token_detail(reason: str) -> str:
    return {
        "missing_token": "Authorization token is required.",
        "not_found": "Authorization link was not found.",
        "expired": "This authorization link has expired. Contact your travel advisor for a new link.",
        "invalid_status": "This authorization link has already been used or is no longer active.",
    }.get(reason, "Authorization link is not valid.")


def _invalid_token_status_code(reason: str) -> int:
    if reason == "not_found":
        return 404
    return 410


async def get_cc_auth_portal_context(db: Session, token: str) -> dict:
    auth_service = CCAuthService(db)
    validation = await auth_service.validate_token(token)
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

    accepted_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.travel_request_id == request.id,
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_ACCEPTED,
        )
        .order_by(ProposedCruise.departure_date, ProposedCruise.id)
        .all()
    )
    if not accepted_cruises:
        raise HTTPException(
            status_code=409,
            detail="Accepted cruise details are not available for this authorization.",
        )

    cruise_summaries, total_deposit = build_cc_auth_cruise_summaries(request, accepted_cruises)
    settings_row = get_agency_settings_row(db, agency_id=agency_id)
    agency_name = settings_row.agency_name
    branding = build_portal_branding_payload(settings_row)

    cruises_payload = []
    for summary, cruise in zip(cruise_summaries, sorted(accepted_cruises, key=lambda item: (item.departure_date, item.id))):
        cruises_payload.append(
            {
                "cruise_line": summary.cruise_line,
                "ship": summary.ship,
                "sailing_date": summary.sailing_date,
                "cabin_type": summary.cabin_type,
                "deposit_amount": str(summary.deposit_amount),
                "final_payment_due_date": summary.final_payment_due_date,
                "itinerary_name": cruise.itinerary_name,
                "number_of_nights": cruise.number_of_nights,
            }
        )

    return {
        "valid": True,
        "passenger_name": f"{request.first_name} {request.last_name}".strip(),
        "passenger_email": request.email.strip(),
        "agency_name": agency_name,
        "cruises": cruises_payload,
        "total_deposit_due": str(total_deposit),
        "expires_at": validation["expires_at"],
        "authorization_id": validation["authorization_id"],
        "branding": branding,
    }


async def complete_cc_auth_portal(db: Session, token: str, card_payload: dict[str, str]) -> dict:
    validation = await CCAuthService(db).validate_token(token)
    if validation.get("valid"):
        set_current_agency_id(validation["agency_id"])
    return await CCAuthService(db).complete_authorization(token, card_payload)