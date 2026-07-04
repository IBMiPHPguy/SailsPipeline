from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.schemas import PublicRegisterRequest, TokenResponse, UserRead
from app.security import create_access_token
from app.services.public_registration_service import register_public_tenant
from app.services.welcome_email_service import dispatch_tenant_welcome_email

router = APIRouter(prefix="/api/public", tags=["public"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
async def register_agency_workspace(
    request: Request,
    payload: PublicRegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not settings.allow_public_registration:
        raise HTTPException(status_code=403, detail="Public registration is disabled.")

    user, agency = register_public_tenant(
        db,
        agency_name=payload.agency_name,
        admin_email=payload.admin_email,
        admin_name=payload.admin_name,
        password=payload.password,
    )

    await dispatch_tenant_welcome_email(
        db,
        user=user,
        agency=agency,
        admin_name=payload.admin_name,
    )

    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))
