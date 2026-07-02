from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    SendMasterTermsEmailRequest,
    SendMasterTermsEmailResponse,
    TermsAcceptResponse,
    TermsRequestStatusResponse,
    TermsValidateResponse,
)
from app.services.request_service import get_open_request
from app.services.tc_communication_service import send_master_terms_email
from app.services.tc_portal_service import complete_terms_portal, get_terms_portal_context
from app.services.tc_service import TCService

router = APIRouter(prefix="/api/terms", tags=["terms"])
request_router = APIRouter(prefix="/api/requests/{request_id}/terms", tags=["terms"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return ""


@router.get("/validate/{token}", response_model=TermsValidateResponse)
@limiter.limit(settings.auth_rate_limit)
async def validate_terms_token_route(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> TermsValidateResponse:
    payload = await get_terms_portal_context(db, token)
    return TermsValidateResponse.model_validate(payload)


@router.post("/accept/{token}", response_model=TermsAcceptResponse)
@limiter.limit(settings.auth_rate_limit)
async def accept_terms_route(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> TermsAcceptResponse:
    result = await complete_terms_portal(db, token, _client_ip(request))
    return TermsAcceptResponse.model_validate(result)


@router.post("/send", response_model=SendMasterTermsEmailResponse)
async def send_master_terms_email_route(
    payload: SendMasterTermsEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendMasterTermsEmailResponse:
    travel_request = get_open_request(db, payload.travel_request_id)
    result = await send_master_terms_email(db, request=travel_request, current_user=current_user)
    return SendMasterTermsEmailResponse.model_validate(result)


@request_router.get("/status", response_model=TermsRequestStatusResponse)
async def get_terms_status_for_request_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> TermsRequestStatusResponse:
    status = await TCService(db).check_request_status(request_id)
    return TermsRequestStatusResponse.model_validate(status)
