from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import Agency, User
from app.rate_limit import limiter
from app.schemas import (
    AgencyBusinessAddressUpdate,
    AgencyInviteCreate,
    AgencyInviteCreated,
    AgencyPendingInvite,
    AgencyProfileRead,
    AgencyTeamMember,
    AgencyTeamSummary,
    AgencyUserUpdate,
    UserRead,
)
from app.services.agency_invite_email_service import dispatch_agency_invite_email
from app.services.agency_invite_service import (
    agency_invitation_token_status,
    cancel_agency_invitation,
    create_agency_invitation,
    get_agency_team,
    update_agency_user,
)
from app.services.agency_service import get_agency_profile, update_agency_business_address

router = APIRouter(prefix="/api/agency", tags=["agency"])


@router.get("/profile", response_model=AgencyProfileRead)
def read_agency_profile(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyProfileRead:
    agency = get_agency_profile(db, agency_id=current_user.agency_id)
    return AgencyProfileRead.model_validate(agency)


@router.patch("/profile", response_model=AgencyProfileRead)
def patch_agency_business_address(
    payload: AgencyBusinessAddressUpdate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyProfileRead:
    agency = update_agency_business_address(
        db,
        agency_id=current_user.agency_id,
        business_address_line_1=payload.business_address_line_1,
        business_address_line_2=payload.business_address_line_2,
        business_city=payload.business_city,
        business_state_or_province=payload.business_state_or_province,
        business_postal_code=payload.business_postal_code,
        business_country=payload.business_country,
    )
    return AgencyProfileRead.model_validate(agency)


@router.get("/team", response_model=AgencyTeamSummary)
def read_agency_team(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyTeamSummary:
    team = get_agency_team(db, current_user.agency_id)
    return AgencyTeamSummary(
        users=[AgencyTeamMember.model_validate(user) for user in team["users"]],
        invitations=[
            AgencyPendingInvite(
                id=invitation.id,
                invite_email=invitation.invite_email,
                role=invitation.role,
                expires_at=invitation.expires_at,
                token_status=agency_invitation_token_status(invitation),
            )
            for invitation in team["invitations"]
        ],
    )


@router.post("/invites", response_model=AgencyInviteCreated, status_code=201)
@limiter.limit(settings.auth_rate_limit)
async def issue_agency_invitation(
    request: Request,
    payload: AgencyInviteCreate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyInviteCreated:
    invitation = create_agency_invitation(
        db,
        agency_id=current_user.agency_id,
        invite_email=payload.invite_email,
        role=payload.role,
    )
    agency = db.get(Agency, current_user.agency_id)
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found.")

    await dispatch_agency_invite_email(
        db,
        agency=agency,
        inviting_user=current_user,
        invitation=invitation,
    )

    return AgencyInviteCreated(
        invitation_id=invitation.id,
        onboarding_path=f"/register-agent?token={invitation.token}",
        expires_at=invitation.expires_at,
    )


@router.delete("/invites/{invitation_id}", status_code=204)
def revoke_agency_invitation(
    invitation_id: str,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> None:
    cancel_agency_invitation(db, agency_id=current_user.agency_id, invitation_id=invitation_id)


@router.patch("/users/{user_id}", response_model=UserRead)
def patch_agency_user(
    user_id: int,
    payload: AgencyUserUpdate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> UserRead:
    user = update_agency_user(
        db,
        agency_id=current_user.agency_id,
        user_id=user_id,
        acting_user_id=current_user.id,
        role=payload.role,
        is_active=payload.is_active,
        email=payload.email,
    )
    return UserRead.model_validate(user)
