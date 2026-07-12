from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agency_email_branding import load_agency_email_branding
from app.constants import COMMUNICATION_STATUS_SENT, COMMUNICATION_TYPE_INSURANCE_WAIVER, INSURANCE_WAIVER_EMAIL_SUBJECT
from app.insurance_email import (
    INSURANCE_WAIVER_CONTENT_END,
    INSURANCE_WAIVER_CONTENT_START,
    build_insurance_waiver_email_html,
)
from app.models import TravelRequest, User
from app.services.communication_service import create_communication
from app.services.email_service import EmailDeliveryService, render_email_logo_only_base_html
from app.services.insurance_service import InsuranceService
from app.user_display import format_username_display_name


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
    status = await insurance_service.get_request_status(request.id)
    if status.get("waiver_signed"):
        raise HTTPException(
            status_code=409,
            detail="The insurance waiver is already signed. A new waiver email cannot be sent.",
        )

    portal_url, had_active_pending = await insurance_service.create_waiver_request(request.id)

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
    agent_name = format_username_display_name(current_user.username) or current_user.username
    html_content = render_email_logo_only_base_html(
        content=inner_html,
        agent_name=agent_name,
        branding=branding,
        email_signature=current_user.email_signature_block,
    )

    email_service = EmailDeliveryService(db)
    success = await email_service.send_transactional_email(
        agency_id=request.agency_id,
        user_id=str(current_user.id),
        agency_name=branding.agency_name,
        agent_email=current_user.email,
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

    create_communication(
        db,
        request=request,
        current_user=current_user,
        request_id=request.id,
        request_workflow_live_id=None,
        communication_type=COMMUNICATION_TYPE_INSURANCE_WAIVER,
        subject=INSURANCE_WAIVER_EMAIL_SUBJECT,
        body=html_content,
        status=COMMUNICATION_STATUS_SENT,
        sender_email=current_user.email,
    )

    return {
        "message": (
            "Insurance waiver email resent via SailsPipeline. The previous secure link is no longer active."
            if had_active_pending
            else "Insurance waiver email sent via SailsPipeline."
        ),
        "resent": had_active_pending,
        "portal_url": portal_url,
        "email_sent": True,
        "recipient": request.email.strip(),
    }
