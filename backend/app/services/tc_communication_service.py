from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agency_email_branding import load_agency_email_branding
from app.constants import COMMUNICATION_STATUS_SENT, COMMUNICATION_TYPE_MASTER_TERMS, TC_EMAIL_SUBJECT
from app.models import TravelRequest, User
from app.services.communication_service import create_communication
from app.services.email_service import EmailDeliveryService, render_email_base_html
from app.services.tc_service import TCService
from app.tc_email import TC_CONTENT_END, TC_CONTENT_START, build_master_terms_email_html


def _extract_terms_inner_content(html: str) -> str:
    start = html.find(TC_CONTENT_START)
    end = html.find(TC_CONTENT_END)
    if start != -1 and end != -1 and end > start:
        return html[start + len(TC_CONTENT_START) : end].strip()
    return html.strip()


async def send_master_terms_email(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
) -> dict[str, object]:
    if not request.email.strip():
        raise HTTPException(status_code=400, detail="Travel request is missing a client email address.")

    tc_service = TCService(db)
    _, client_id = tc_service.resolve_client_id_for_request(request.id)
    existing = await tc_service.check_global_status(client_id, request.agency_id)
    if existing.get("on_file"):
        raise HTTPException(
            status_code=409,
            detail="Master Terms & Conditions are already on file for this client.",
        )

    portal_url = await tc_service.create_tc_request(request.id)

    passenger_name = f"{request.first_name} {request.last_name}".strip()
    branding = load_agency_email_branding(db, agency_id=request.agency_id)

    inner_content = build_master_terms_email_html(
        passenger_name=passenger_name,
        agency_name=branding.agency_name,
        portal_url=portal_url,
        primary_color=branding.primary_color,
        primary_text_color=branding.primary_text_color,
    )
    inner_html = _extract_terms_inner_content(inner_content)
    html_content = render_email_base_html(
        content=inner_html,
        agent_name=current_user.username,
        branding=branding,
    )

    email_service = EmailDeliveryService(db)
    success = await email_service.send_transactional_email(
        agency_id=request.agency_id,
        user_id=str(current_user.id),
        agency_name=branding.agency_name,
        agent_email=current_user.email,
        recipient=request.email.strip(),
        email_type=COMMUNICATION_TYPE_MASTER_TERMS,
        subject=TC_EMAIL_SUBJECT,
        html_content=html_content,
        travel_request_id=str(request.id),
    )
    if not success:
        raise HTTPException(
            status_code=502,
            detail="Master Terms & Conditions email could not be delivered. Check agency email logs.",
        )

    create_communication(
        db,
        request=request,
        current_user=current_user,
        request_id=request.id,
        request_workflow_live_id=None,
        communication_type=COMMUNICATION_TYPE_MASTER_TERMS,
        subject=TC_EMAIL_SUBJECT,
        body=html_content,
        status=COMMUNICATION_STATUS_SENT,
        sender_email=current_user.email,
    )

    return {
        "message": "Master Terms & Conditions review email sent via SailsPipeline.",
        "portal_url": portal_url,
        "email_sent": True,
        "recipient": request.email.strip(),
    }
