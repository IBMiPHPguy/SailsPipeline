from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    CcAuthCardPayload,
    CcAuthCompleteResponse,
    CcAuthPurgeResponse,
    CcAuthRevealResponse,
    CcAuthSummaryRead,
    CcAuthValidateResponse,
    CcAuthVaultAccessRequest,
    SendCcAuthEmailRequest,
    SendCcAuthEmailResponse,
)
from app.services.cc_auth_agent_service import (
    list_request_cc_authorizations,
    purge_request_cc_authorization,
    reveal_request_cc_authorization,
)
from app.services.cc_auth_communication_service import send_cc_auth_email
from app.services.cc_auth_portal_service import complete_cc_auth_portal, get_cc_auth_portal_context
from app.services.request_service import get_open_request

router = APIRouter(prefix="/api/cc-auth", tags=["cc-auth"])
agent_router = APIRouter(prefix="/api/requests/{request_id}/cc-auth", tags=["cc-auth"])


@router.get("/validate/{token}", response_model=CcAuthValidateResponse)
@limiter.limit(settings.auth_rate_limit)
async def validate_cc_auth_token_route(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> CcAuthValidateResponse:
    payload = await get_cc_auth_portal_context(db, token)
    return CcAuthValidateResponse.model_validate(payload)


@router.post("/complete/{token}", response_model=CcAuthCompleteResponse)
@limiter.limit(settings.auth_rate_limit)
async def complete_cc_auth_route(
    request: Request,
    token: str,
    payload: CcAuthCardPayload,
    db: Session = Depends(get_db),
) -> CcAuthCompleteResponse:
    result = await complete_cc_auth_portal(db, token, payload.model_dump())
    return CcAuthCompleteResponse.model_validate(result)


@router.post("/send", response_model=SendCcAuthEmailResponse)
async def send_cc_auth_email_route(
    payload: SendCcAuthEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendCcAuthEmailResponse:
    request = get_open_request(db, payload.travel_request_id)
    result = await send_cc_auth_email(db, request=request, current_user=current_user)
    return SendCcAuthEmailResponse.model_validate(result)


@agent_router.get("", response_model=list[CcAuthSummaryRead])
def list_request_cc_authorizations_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CcAuthSummaryRead]:
    records = list_request_cc_authorizations(db, request_id=request_id)
    return [CcAuthSummaryRead.model_validate(record) for record in records]


@agent_router.post("/{authorization_id}/reveal", response_model=CcAuthRevealResponse)
@limiter.limit(settings.auth_rate_limit)
def reveal_request_cc_authorization_route(
    request: Request,
    request_id: int,
    authorization_id: str,
    payload: CcAuthVaultAccessRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CcAuthRevealResponse:
    result = reveal_request_cc_authorization(
        db,
        request_id=request_id,
        authorization_id=authorization_id,
        vault_access_key=payload.vault_access_key,
    )
    return CcAuthRevealResponse.model_validate(result)


@agent_router.post("/{authorization_id}/purge", response_model=CcAuthPurgeResponse)
def purge_request_cc_authorization_route(
    request_id: int,
    authorization_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CcAuthPurgeResponse:
    result = purge_request_cc_authorization(db, request_id=request_id, authorization_id=authorization_id)
    return CcAuthPurgeResponse.model_validate(result)
