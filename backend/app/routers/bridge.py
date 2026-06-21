from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import require_platform_super_admin
from app.models import User
from app.rate_limit import limiter
from app.schemas import (
    BridgeAgencySummary,
    BridgeInvitationSummary,
    BridgeSummaryResponse,
    BridgeTenantDetail,
    BridgeTenantUpdate,
    BridgeTenantUserSummary,
    PlatformInviteCreate,
    PlatformInviteCreated,
)
from app.services.bridge_service import (
    cancel_platform_invitation,
    create_platform_invitation,
    get_bridge_summary,
    get_bridge_tenant_detail,
    invitation_token_status,
    update_bridge_tenant,
)

router = APIRouter(prefix="/api/bridge", tags=["bridge"])


@router.get("/summary", response_model=BridgeSummaryResponse)
def bridge_summary(
    _admin: User = Depends(require_platform_super_admin),
    db: Session = Depends(get_db),
) -> BridgeSummaryResponse:
    summary = get_bridge_summary(db)
    return BridgeSummaryResponse(
        agencies=[BridgeAgencySummary.model_validate(agency) for agency in summary["agencies"]],
        invitations=[
            BridgeInvitationSummary(
                id=invitation.id,
                target_agency_name=invitation.target_agency_name,
                target_organization_handle=invitation.target_organization_handle,
                invite_email=invitation.invite_email,
                expires_at=invitation.expires_at,
                is_used=invitation.is_used,
                token_status=invitation_token_status(invitation),
            )
            for invitation in summary["invitations"]
        ],
    )


@router.get("/tenants/{agency_id}", response_model=BridgeTenantDetail)
def bridge_tenant_detail(
    agency_id: str,
    _admin: User = Depends(require_platform_super_admin),
    db: Session = Depends(get_db),
) -> BridgeTenantDetail:
    detail = get_bridge_tenant_detail(db, agency_id)
    return BridgeTenantDetail(
        agency=BridgeAgencySummary.model_validate(detail["agency"]),
        users=[BridgeTenantUserSummary.model_validate(user) for user in detail["users"]],
    )


@router.patch("/tenants/{agency_id}", response_model=BridgeAgencySummary)
@limiter.limit(settings.auth_rate_limit)
def bridge_tenant_update(
    request: Request,
    agency_id: str,
    payload: BridgeTenantUpdate,
    _admin: User = Depends(require_platform_super_admin),
    db: Session = Depends(get_db),
) -> BridgeAgencySummary:
    agency = update_bridge_tenant(
        db,
        agency_id,
        name=payload.name,
        organization_handle=payload.organization_handle,
        subscription_state=payload.subscription_state,
    )
    return BridgeAgencySummary.model_validate(agency)


@router.post("/invites", response_model=PlatformInviteCreated, status_code=201)
@limiter.limit(settings.auth_rate_limit)
def issue_platform_invitation(
    request: Request,
    payload: PlatformInviteCreate,
    _admin: User = Depends(require_platform_super_admin),
    db: Session = Depends(get_db),
) -> PlatformInviteCreated:
    invitation = create_platform_invitation(
        db,
        target_agency_name=payload.target_agency_name,
        target_organization_handle=payload.target_organization_handle,
        invite_email=str(payload.invite_email),
    )
    return PlatformInviteCreated(
        invitation_id=invitation.id,
        onboarding_path=f"/register?token={invitation.token}",
        expires_at=invitation.expires_at,
    )


@router.delete("/invites/{invitation_id}", status_code=204)
def revoke_platform_invitation(
    invitation_id: str,
    _admin: User = Depends(require_platform_super_admin),
    db: Session = Depends(get_db),
) -> None:
    cancel_platform_invitation(db, invitation_id)
