from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Agency, User
from app.rate_limit import limiter
from app.schemas import BridgeLogin, TokenResponse, UserCreate, UserLogin, UserRead
from app.security import create_access_token
from app.services.auth_service import authenticate_agency_user, authenticate_platform_operator
from app.services.subscription_service import raise_if_login_blocked

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_FAILURE_DETAIL = "Incorrect organization handle, username, or password."
BRIDGE_LOGIN_FAILURE_DETAIL = "Incorrect username or password."


@router.post("/bridge/login", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
def bridge_login(
    request: Request,
    payload: BridgeLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_platform_operator(
        db,
        username=payload.username,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=BRIDGE_LOGIN_FAILURE_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/register", response_model=UserRead, status_code=201)
@limiter.limit(settings.auth_rate_limit)
def register_user(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Legacy registration is disabled. Use POST /api/public/register to provision a new agency workspace.",
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.auth_rate_limit)
def login(
    request: Request,
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_agency_user(
        db,
        organization_handle=payload.organization_handle,
        username=payload.username,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_FAILURE_DETAIL,
            headers={"WWW-Authenticate": "Bearer"},
        )

    agency = db.get(Agency, user.agency_id)
    if agency is not None:
        raise_if_login_blocked(db, agency)

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
