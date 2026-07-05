from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.agency_email_branding import load_agency_email_branding
from app.constants import (
    COMMUNICATION_STATUS_DRAFT,
    COMMUNICATION_STATUS_SENT,
    COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
    PROPOSED_CRUISE_STATUS_PROPOSED,
)
from app.gemini_service import (
    GeminiConfigurationError,
    GeminiParseError,
    generate_research_communication_from_proposals,
)
from app.models import ProposedCruise, RequestCommunication, RequestWorkflowLive, TravelRequest, User
from app.research_proposal_email import build_research_proposal_email_html
from app.schemas import GenerateResearchCommunicationResponse
from app.services.agency_service import assert_child_belongs_to_request, require_record_for_agency
from app.services.email_service import EmailDeliveryService, extract_communication_html_content, render_email_base_html
from app.services.gemini_config_service import resolve_gemini_credentials
from app.services.gemini_context_service import (
    build_request_context_for_gemini,
    proposed_cruise_to_gemini_dict,
    validate_proposed_cruises_for_proposal_email,
)
from app.services.request_service import touch_request


def load_communication(db: Session, communication_id: int) -> RequestCommunication:
    return (
        db.query(RequestCommunication)
        .options(
            joinedload(RequestCommunication.created_by),
            joinedload(RequestCommunication.updated_by),
        )
        .filter(RequestCommunication.id == communication_id)
        .one()
    )


def build_research_proposal_communication_subject(request: TravelRequest, option_count: int) -> str:
    destination = request.destination.strip() or "Travel request"
    option_label = "option" if option_count == 1 else "options"
    return f"Cruise Proposal – {destination} ({option_count} {option_label})"[:255]


def _assert_workflow_belongs_to_request(
    db: Session,
    *,
    request: TravelRequest,
    request_workflow_live_id: str | None,
) -> None:
    if request_workflow_live_id is None:
        return
    workflow = db.get(RequestWorkflowLive, request_workflow_live_id)
    require_record_for_agency(workflow, agency_id=request.agency_id)
    assert_child_belongs_to_request(
        child_agency_id=workflow.agency_id,
        child_travel_request_id=workflow.travel_request_id,
        request_id=request.id,
        agency_id=request.agency_id,
    )


def find_draft_research_proposal_communication(
    db: Session,
    request_id: int,
    request_workflow_live_id: str | None,
) -> RequestCommunication | None:
    query = db.query(RequestCommunication).filter(
        RequestCommunication.travel_request_id == request_id,
        RequestCommunication.communication_type == COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
        RequestCommunication.status == COMMUNICATION_STATUS_DRAFT,
    )
    if request_workflow_live_id is None:
        query = query.filter(RequestCommunication.request_workflow_live_id.is_(None))
    else:
        query = query.filter(RequestCommunication.request_workflow_live_id == request_workflow_live_id)
    return query.order_by(RequestCommunication.updated_at.desc()).first()


def save_research_proposal_communication(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
    subject: str,
    body: str,
    request_workflow_live_id: str | None,
) -> RequestCommunication:
    _assert_workflow_belongs_to_request(
        db,
        request=request,
        request_workflow_live_id=request_workflow_live_id,
    )

    communication = find_draft_research_proposal_communication(db, request.id, request_workflow_live_id)
    if communication is None:
        communication = RequestCommunication(
            agency_id=request.agency_id,
            travel_request_id=request.id,
            request_workflow_live_id=request_workflow_live_id,
            communication_type=COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
            subject=subject.strip(),
            body=body,
            status=COMMUNICATION_STATUS_DRAFT,
            created_by_id=current_user.id,
            updated_by_id=current_user.id,
        )
        db.add(communication)
    else:
        communication.subject = subject.strip()
        communication.body = body
        communication.updated_by_id = current_user.id

    touch_request(request, current_user)
    db.commit()
    return load_communication(db, communication.id)


def generate_research_communication_from_proposed_cruises(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
    request_workflow_live_id: str | None,
) -> GenerateResearchCommunicationResponse:
    proposed_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.travel_request_id == request.id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_PROPOSED,
        )
        .order_by(ProposedCruise.departure_date, ProposedCruise.id)
        .all()
    )
    validated_cruises = validate_proposed_cruises_for_proposal_email(proposed_cruises)
    request_context = build_request_context_for_gemini(request)
    cruise_payload = [
        proposed_cruise_to_gemini_dict(cruise, index)
        for index, cruise in enumerate(validated_cruises, start=1)
    ]

    try:
        api_key, model_name = resolve_gemini_credentials(db, agency_id=request.agency_id)
        email_subject, intro, closing, model_name = generate_research_communication_from_proposals(
            api_key=api_key,
            model_name=model_name,
            request_context=request_context,
            proposed_cruises=cruise_payload,
        )
        body = build_research_proposal_email_html(
            intro=intro,
            closing=closing,
            cruises=validated_cruises,
        )
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    communication_subject = build_research_proposal_communication_subject(request, len(validated_cruises))
    communication = save_research_proposal_communication(
        db,
        request=request,
        current_user=current_user,
        subject=communication_subject,
        body=body,
        request_workflow_live_id=request_workflow_live_id,
    )

    return GenerateResearchCommunicationResponse(
        model=model_name,
        proposed_cruise_count=len(validated_cruises),
        subject=communication_subject,
        email_subject=email_subject,
        body=body,
        communication=communication,
    )


def create_communication(
    db: Session,
    *,
    request: TravelRequest,
    current_user: User,
    request_id: int,
    request_workflow_live_id: str | None,
    communication_type: str,
    subject: str,
    body: str,
    status: str,
    sender_email: str | None = None,
    received_at: datetime | None = None,
    is_response_to_agent: bool = False,
) -> RequestCommunication:
    _assert_workflow_belongs_to_request(
        db,
        request=request,
        request_workflow_live_id=request_workflow_live_id,
    )

    communication = RequestCommunication(
        agency_id=request.agency_id,
        travel_request_id=request_id,
        request_workflow_live_id=request_workflow_live_id,
        communication_type=communication_type,
        subject=subject.strip(),
        body=body,
        sender_email=sender_email.strip() if sender_email else None,
        status=status,
        received_at=received_at,
        is_response_to_agent=is_response_to_agent,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    if status == COMMUNICATION_STATUS_SENT:
        communication.sent_at = datetime.now(UTC).replace(tzinfo=None)

    touch_request(request, current_user)
    db.add(communication)
    db.commit()
    return load_communication(db, communication.id)


def update_communication_record(
    db: Session,
    *,
    request: TravelRequest,
    communication: RequestCommunication,
    current_user: User,
    updates: dict,
) -> RequestCommunication:
    for field, value in updates.items():
        if field in {"subject", "communication_type", "body", "status", "sender_email"} and value is not None:
            setattr(communication, field, value.strip() if field in {"subject", "sender_email"} else value)
        elif field == "received_at":
            if value is not None:
                setattr(communication, field, value)
        elif field == "is_response_to_agent":
            setattr(communication, field, bool(value))

    if updates.get("status") == COMMUNICATION_STATUS_SENT and communication.sent_at is None:
        communication.sent_at = datetime.now(UTC).replace(tzinfo=None)

    communication.updated_by_id = current_user.id
    touch_request(request, current_user)
    db.commit()
    return load_communication(db, communication.id)


async def send_research_communication_via_email(
    db: Session,
    *,
    request: TravelRequest,
    communication: RequestCommunication,
    current_user: User,
) -> RequestCommunication:
    if communication.communication_type != COMMUNICATION_TYPE_RESEARCH_PROPOSAL:
        raise HTTPException(
            status_code=400,
            detail="Only research proposal communications can be sent via SailsPipeline.",
        )
    if communication.status == COMMUNICATION_STATUS_SENT:
        raise HTTPException(status_code=400, detail="This communication has already been sent.")

    recipient = request.email.strip()
    if not recipient:
        raise HTTPException(status_code=400, detail="Travel request has no client email address.")

    branding = load_agency_email_branding(db, agency_id=request.agency_id)
    inner_content = extract_communication_html_content(communication.body)
    html_content = render_email_base_html(
        content=inner_content,
        agent_name=current_user.username,
        branding=branding,
    )

    email_service = EmailDeliveryService(db)
    success = await email_service.send_transactional_email(
        agency_id=request.agency_id,
        user_id=str(current_user.id),
        agency_name=branding.agency_name,
        agent_email=current_user.email,
        recipient=recipient,
        email_type=COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
        subject=communication.subject,
        html_content=html_content,
        travel_request_id=str(request.id),
    )
    if not success:
        raise HTTPException(
            status_code=502,
            detail="Failed to send email. Check agency email logs for details.",
        )

    return update_communication_record(
        db,
        request=request,
        communication=communication,
        current_user=current_user,
        updates={"status": COMMUNICATION_STATUS_SENT},
    )


def delete_draft_communication(
    db: Session,
    *,
    request: TravelRequest,
    communication: RequestCommunication,
    current_user: User,
) -> None:
    from app.constants import COMMUNICATION_STATUS_DRAFT, COMMUNICATION_TYPE_INBOUND_EMAIL

    if communication.communication_type == COMMUNICATION_TYPE_INBOUND_EMAIL:
        db.delete(communication)
        touch_request(request, current_user)
        db.commit()
        return

    if communication.status != COMMUNICATION_STATUS_DRAFT:
        raise HTTPException(status_code=400, detail="Only draft communications can be deleted.")

    db.delete(communication)
    touch_request(request, current_user)
    db.commit()
