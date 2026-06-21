from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token
from app.tenant_context import clear_current_agency_id, set_current_agency_id
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN

bearer_scheme = HTTPBearer(auto_error=False)

PLATFORM_OPERATOR_API_PREFIXES = (
    "/api/bridge",
    "/api/auth/login",
    "/api/auth/bridge/login",
    "/api/auth/me",
    "/api/health",
)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_query = (
        db.query(User)
        .filter(
            User.id == claims.user_id,
            User.role == claims.role,
            User.is_active.is_(True),
        )
    )
    if claims.agency_id is None:
        user_query = user_query.filter(User.agency_id.is_(None))
    else:
        user_query = user_query.filter(User.agency_id == claims.agency_id)

    user = user_query.first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.role == USER_ROLE_PLATFORM_SUPER_ADMIN:
        path = request.url.path
        if not any(path.startswith(prefix) for prefix in PLATFORM_OPERATOR_API_PREFIXES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform operators must use The Bridge.",
            )
        clear_current_agency_id()
    elif user.agency_id is not None:
        set_current_agency_id(user.agency_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant membership required.",
        )

    return user


def require_platform_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != USER_ROLE_PLATFORM_SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bridge access requires platform super admin role.",
        )
    return current_user


def require_tenant_super_user(current_user: User = Depends(get_current_user)) -> User:
    from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER

    if current_user.role != USER_ROLE_TENANT_SUPER_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team management requires tenant super user role.",
        )
    if current_user.agency_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant membership required.",
        )
    return current_user
