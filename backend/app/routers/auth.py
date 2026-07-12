from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.brand_logo_storage import (
    externalize_inline_user_signature_images,
    purge_stale_local_user_avatar,
    upload_user_avatar,
    upload_user_signature_image,
)
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Agency, User
from app.rate_limit import limiter
from app.schemas import (
    BridgeLogin,
    TokenResponse,
    UserAvatarUploadResponse,
    UserCreate,
    UserLogin,
    UserRead,
    UserSignatureImageUploadResponse,
    UserSignatureUpdate,
)
from app.security import create_access_token
from app.services.auth_service import authenticate_agency_user, authenticate_platform_operator
from app.services.subscription_service import raise_if_login_blocked
from app.services.user_read_service import user_to_read

router = APIRouter(prefix="/api/auth", tags=["auth"])

LOGIN_FAILURE_DETAIL = "Incorrect organization handle, username, or password."
BRIDGE_LOGIN_FAILURE_DETAIL = "Incorrect username or password."
_MAX_AVATAR_BYTES = 5 * 1024 * 1024


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
    return TokenResponse(access_token=token, user=user_to_read(db, user))


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
    return TokenResponse(access_token=token, user=user_to_read(db, user))


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return user_to_read(db, current_user)


@router.put("/me/signature", response_model=UserRead)
def update_current_user_signature(
    payload: UserSignatureUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    normalized = (payload.email_signature_block or "").strip() or None
    if normalized:
        try:
            normalized = externalize_inline_user_signature_images(
                current_user.id,
                normalized,
                agency_id=current_user.agency_id,
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
    current_user.email_signature_block = normalized
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_to_read(db, current_user)


@router.post("/me/avatar", response_model=UserAvatarUploadResponse)
async def upload_current_user_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserAvatarUploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Avatar upload must be an image file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Avatar file is empty.")
    if len(content) > _MAX_AVATAR_BYTES:
        raise HTTPException(status_code=422, detail="Avatar file must be 5 MB or smaller.")

    purge_stale_local_user_avatar(current_user.avatar_url)

    try:
        avatar_url = upload_user_avatar(
            current_user.id,
            content,
            filename=file.filename,
            content_type=file.content_type,
            agency_id=current_user.agency_id,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    current_user.avatar_url = avatar_url
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return UserAvatarUploadResponse(avatar_url=avatar_url)


@router.delete("/me/avatar", response_model=UserRead)
def delete_current_user_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    purge_stale_local_user_avatar(current_user.avatar_url)
    current_user.avatar_url = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return user_to_read(db, current_user)


@router.post("/me/signature-image", response_model=UserSignatureImageUploadResponse)
async def upload_current_user_signature_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> UserSignatureImageUploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Signature image upload must be an image file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Signature image file is empty.")

    try:
        image_url = upload_user_signature_image(
            current_user.id,
            content,
            filename=file.filename,
            content_type=file.content_type,
            agency_id=current_user.agency_id,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return UserSignatureImageUploadResponse(image_url=image_url)
