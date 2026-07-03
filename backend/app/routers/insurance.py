from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    AnnualInsuranceUpdate,
    InsuranceRequestStatusResponse,
    InsuranceWaiverSignResponse,
    InsuranceWaiverValidateResponse,
    SendInsuranceWaiverEmailRequest,
    SendInsuranceWaiverEmailResponse,
)
from app.services.insurance_communication_service import send_insurance_waiver_email
from app.services.insurance_portal_service import complete_insurance_waiver_portal, get_insurance_waiver_portal_context
from app.services.insurance_service import InsuranceService
from app.services.request_service import get_open_request

router = APIRouter(prefix="/api/insurance", tags=["insurance"])
request_router = APIRouter(prefix="/api/requests/{request_id}/insurance", tags=["insurance"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return ""


@router.get("/validate/{token}", response_model=InsuranceWaiverValidateResponse)
@limiter.limit(settings.auth_rate_limit)
async def validate_insurance_waiver_token_route(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> InsuranceWaiverValidateResponse:
    payload = await get_insurance_waiver_portal_context(db, token)
    return InsuranceWaiverValidateResponse.model_validate(payload)


@router.post("/waiver/{token}", response_model=InsuranceWaiverSignResponse)
@limiter.limit(settings.auth_rate_limit)
async def sign_insurance_waiver_route(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> InsuranceWaiverSignResponse:
    result = await complete_insurance_waiver_portal(db, token, _client_ip(request))
    return InsuranceWaiverSignResponse.model_validate(result)


@router.post("/send-waiver", response_model=SendInsuranceWaiverEmailResponse)
async def send_insurance_waiver_email_route(
    payload: SendInsuranceWaiverEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SendInsuranceWaiverEmailResponse:
    travel_request = get_open_request(db, payload.travel_request_id)
    result = await send_insurance_waiver_email(db, request=travel_request, current_user=current_user)
    return SendInsuranceWaiverEmailResponse.model_validate(result)


@request_router.get("/status", response_model=InsuranceRequestStatusResponse)
async def get_insurance_status_for_request_route(
    request_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InsuranceRequestStatusResponse:
    status = await InsuranceService(db).get_request_status(request_id)
    return InsuranceRequestStatusResponse.model_validate(status)


@request_router.patch("/annual")
async def update_annual_insurance_route(
    request_id: int,
    payload: AnnualInsuranceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InsuranceRequestStatusResponse:
    InsuranceService(db).update_annual_insurance(
        travel_request_id=request_id,
        payload=payload,
        current_user=current_user,
    )
    status = await InsuranceService(db).get_request_status(request_id)
    return InsuranceRequestStatusResponse.model_validate(status)


@request_router.post("/clear-annual", response_model=InsuranceRequestStatusResponse)
async def clear_annual_insurance_route(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InsuranceRequestStatusResponse:
    InsuranceService(db).clear_annual_insurance(
        travel_request_id=request_id,
        current_user=current_user,
    )
    status = await InsuranceService(db).get_request_status(request_id)
    return InsuranceRequestStatusResponse.model_validate(status)
