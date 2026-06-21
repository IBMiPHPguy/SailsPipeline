from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.schemas import AgentInviteRead, OnboardingAccept, OnboardingInviteRead, TokenResponse, UserRead
from app.security import create_access_token
from app.services.agency_invite_service import accept_agency_invitation, get_valid_agency_invitation
from app.services.bridge_service import accept_platform_invitation, get_valid_platform_invitation

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.get("/invites/verify", response_model=OnboardingInviteRead)
@limiter.limit(settings.auth_rate_limit)
def verify_platform_invitation(
    request: Request,
    token: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
) -> OnboardingInviteRead:
    invitation = get_valid_platform_invitation(db, token)
    return OnboardingInviteRead(
        target_agency_name=invitation.target_agency_name,
        organization_handle=invitation.target_organization_handle,
        invite_email=invitation.invite_email,
        expires_at=invitation.expires_at,
    )


@router.post("/accept", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
def accept_onboarding_invitation(
    request: Request,
    payload: OnboardingAccept,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = accept_platform_invitation(
        db,
        token=payload.token,
        full_name=payload.full_name,
        password=payload.password,
    )
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.get("/agent/invites/verify", response_model=AgentInviteRead)
@limiter.limit(settings.auth_rate_limit)
def verify_agent_invitation(
    request: Request,
    token: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
) -> AgentInviteRead:
    invitation = get_valid_agency_invitation(db, token)
    agency = invitation.agency
    return AgentInviteRead(
        agency_name=agency.name,
        organization_handle=agency.organization_handle,
        invite_email=invitation.invite_email,
        role=invitation.role,
        expires_at=invitation.expires_at,
    )


@router.post("/agent/accept", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
def accept_agent_invitation(
    request: Request,
    payload: OnboardingAccept,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = accept_agency_invitation(
        db,
        token=payload.token,
        full_name=payload.full_name,
        password=payload.password,
    )
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))
