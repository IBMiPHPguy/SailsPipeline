from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agency_email_branding import load_agency_email_branding
from app.constants import COMMUNICATION_TYPE_INSURANCE_WAIVER, INSURANCE_WAIVER_EMAIL_SUBJECT
from app.insurance_email import (
    INSURANCE_WAIVER_CONTENT_END,
    INSURANCE_WAIVER_CONTENT_START,
    build_insurance_waiver_email_html,
)
from app.models import TravelRequest, User
from app.services.email_service import EmailDeliveryService, render_email_base_html
from app.services.insurance_service import InsuranceService


def _extract_waiver_inner_content(html: str) -> str:
    start = html.find(INSURANCE_WAIVER_CONTENT_START)
    end = html.find(INSURANCE_WAIVER_CONTENT_END)
    if start != -1 and end != -1 and end > start:
        return html[start + len(INSURANCE_WAIVER_CONTENT_START) : end].strip()
    return html.strip()


async def send_insurance_waiver_email(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
) -> dict[str, object]:
    if not request.email.strip():
        raise HTTPException(status_code=400, detail="Travel request is missing a client email address.")

    insurance_service = InsuranceService(db)
    portal_url = await insurance_service.create_waiver_request(request.id)

    passenger_name = f"{request.first_name} {request.last_name}".strip()
    branding = load_agency_email_branding(db, agency_id=request.agency_id)

    inner_content = build_insurance_waiver_email_html(
        passenger_name=passenger_name,
        agency_name=branding.agency_name,
        portal_url=portal_url,
        primary_color=branding.primary_color,
        primary_text_color=branding.primary_text_color,
    )
    inner_html = _extract_waiver_inner_content(inner_content)
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
        email_type=COMMUNICATION_TYPE_INSURANCE_WAIVER,
        subject=INSURANCE_WAIVER_EMAIL_SUBJECT,
        html_content=html_content,
        travel_request_id=str(request.id),
    )
    if not success:
        raise HTTPException(
            status_code=502,
            detail="Insurance waiver email could not be delivered. Check agency email logs.",
        )

    return {
        "message": "Insurance waiver email sent via SailsPipeline.",
        "portal_url": portal_url,
        "email_sent": True,
        "recipient": request.email.strip(),
    }
