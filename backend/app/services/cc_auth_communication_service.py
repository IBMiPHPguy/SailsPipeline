from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agency_email_branding import load_agency_email_branding
from app.cc_auth_email import CC_AUTH_CONTENT_END, CC_AUTH_CONTENT_START, build_cc_auth_email_html
from app.cc_auth_helpers import build_cc_auth_cruise_summaries
from app.constants import (
    CC_AUTH_EMAIL_SUBJECT,
    COMMUNICATION_TYPE_CC_AUTH,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
)
from app.models import ProposedCruise, TravelRequest, User
from app.services.cc_auth_service import CCAuthService
from app.services.email_service import EmailDeliveryService, render_email_base_html


def _extract_cc_auth_inner_content(html: str) -> str:
    start = html.find(CC_AUTH_CONTENT_START)
    end = html.find(CC_AUTH_CONTENT_END)
    if start != -1 and end != -1 and end > start:
        return html[start + len(CC_AUTH_CONTENT_START) : end].strip()
    return html.strip()


async def send_cc_auth_email(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
) -> dict[str, object]:
    if not request.email.strip():
        raise HTTPException(status_code=400, detail="Travel request is missing a client email address.")

    accepted_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.travel_request_id == request.id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_ACCEPTED,
        )
        .order_by(ProposedCruise.departure_date, ProposedCruise.id)
        .all()
    )
    if not accepted_cruises:
        raise HTTPException(
            status_code=400,
            detail="At least one accepted cruise is required before sending a credit card authorization email.",
        )

    cruise_summaries, total_deposit = build_cc_auth_cruise_summaries(request, accepted_cruises)
    if total_deposit <= 0:
        raise HTTPException(
            status_code=400,
            detail="Deposit amounts must be greater than zero for accepted cruises.",
        )

    auth_service = CCAuthService(db)
    portal_url = await auth_service.create_auth_request(request.id)

    passenger_name = f"{request.first_name} {request.last_name}".strip()
    branding = load_agency_email_branding(db, agency_id=request.agency_id)
    inner_content = build_cc_auth_email_html(
        passenger_name=passenger_name,
        agency_name=branding.agency_name,
        cruises=cruise_summaries,
        total_deposit_due=total_deposit,
        portal_url=portal_url,
        primary_color=branding.primary_color,
        primary_text_color=branding.primary_text_color,
    )
    inner_html = _extract_cc_auth_inner_content(inner_content)

    html_content = render_email_base_html(
        content=inner_html,
        agent_name=current_user.username,
        branding=branding,
    )

    email_service = EmailDeliveryService(db)
    success = await email_service.send_transactional_email(
        agency_id=request.agency_id,
        user_id=str(current_user.id),
        user_name=current_user.username,
        user_email=current_user.email,
        recipient=request.email.strip(),
        email_type=COMMUNICATION_TYPE_CC_AUTH,
        subject=CC_AUTH_EMAIL_SUBJECT,
        html_content=html_content,
        travel_request_id=str(request.id),
    )
    if not success:
        raise HTTPException(
            status_code=502,
            detail="Credit card authorization email could not be delivered. Check agency email logs.",
        )

    return {
        "message": "Credit card authorization email sent via SailsPipeline.",
        "portal_url": portal_url,
        "email_sent": True,
        "recipient": request.email.strip(),
        "total_deposit_due": str(total_deposit),
        "accepted_cruise_count": len(accepted_cruises),
    }
