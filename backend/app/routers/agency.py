from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    AgencyInviteCreate,
    AgencyInviteCreated,
    AgencyPendingInvite,
    AgencyTeamMember,
    AgencyTeamSummary,
    AgencyUserUpdate,
    UserRead,
)
from app.services.agency_invite_service import (
    agency_invitation_token_status,
    cancel_agency_invitation,
    create_agency_invitation,
    get_agency_team,
    update_agency_user,
)

router = APIRouter(prefix="/api/agency", tags=["agency"])


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
def issue_agency_invitation(
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
