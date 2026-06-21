from sqlalchemy.orm import Session

from app.models import Agency, User
from app.security import verify_password
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


def normalize_organization_handle(handle: str) -> str:
    return handle.strip().lower()


def resolve_agency_by_organization_handle(db: Session, organization_handle: str) -> Agency | None:
    normalized = normalize_organization_handle(organization_handle)
    return (
        db.query(Agency)
        .filter(
            Agency.organization_handle == normalized,
            Agency.is_active.is_(True),
        )
        .first()
    )


def authenticate_agency_user(
    db: Session,
    *,
    organization_handle: str,
    username: str,
    password: str,
) -> User | None:
    agency = resolve_agency_by_organization_handle(db, organization_handle)
    if agency is None:
        return None

    user = (
        db.query(User)
        .filter(
            User.username == username.strip(),
            User.agency_id == agency.id,
            User.is_active.is_(True),
        )
        .first()
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def authenticate_platform_operator(
    db: Session,
    *,
    username: str,
    password: str,
) -> User | None:
    user = (
        db.query(User)
        .filter(
            User.username == username.strip(),
            User.role == USER_ROLE_PLATFORM_SUPER_ADMIN,
            User.agency_id.is_(None),
            User.is_active.is_(True),
        )
        .first()
    )
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
