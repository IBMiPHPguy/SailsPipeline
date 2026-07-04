from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter
from app.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    PasswordResetValidateResponse,
    ResetPasswordRequest,
)
from app.security import hash_password
from app.services.password_reset_email_service import dispatch_password_reset_email
from app.services.password_reset_service import (
    FORGOT_PASSWORD_SUCCESS_MESSAGE,
    assert_valid_reset_token,
    find_active_tenant_user_for_password_reset,
    get_password_reset_portal_context,
    issue_password_reset_token,
    reset_user_password,
)

router = APIRouter(prefix="/api/public/auth", tags=["public-auth"])


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.auth_rate_limit)
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = find_active_tenant_user_for_password_reset(
        db,
        organization_handle=payload.organization_handle,
        email=str(payload.email),
    )
    if user is not None:
        raw_token = issue_password_reset_token(db, user)
        await dispatch_password_reset_email(
            db,
            user=user,
            raw_token=raw_token,
            organization_handle=payload.organization_handle.strip(),
        )

    return MessageResponse(message=FORGOT_PASSWORD_SUCCESS_MESSAGE)


@router.get("/reset-password/validate/{token}", response_model=PasswordResetValidateResponse)
@limiter.limit(settings.auth_rate_limit)
async def validate_reset_password_token(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
) -> PasswordResetValidateResponse:
    payload = get_password_reset_portal_context(db, token)
    return PasswordResetValidateResponse.model_validate(payload)


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit(settings.auth_rate_limit)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    user = assert_valid_reset_token(db, payload.token)

    try:
        password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    reset_user_password(db, user, password_hash)
    return MessageResponse(message="Password updated successfully.")
