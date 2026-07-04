from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine
from app.models import User
from app.security import hash_password
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


class BridgeLaunchError(RuntimeError):
    """Raised when the one-time Bridge launch sequence cannot complete."""


@dataclass(frozen=True)
class BridgeLaunchReport:
    schema_ready: bool
    platform_operator_username: str
    platform_operator_created: bool
    platform_operator_count: int
    public_registration_enabled: bool


REQUIRED_SCHEMA_TABLES = (
    "agencies",
    "agency_settings",
    "users",
    "platform_invitations",
)


def verify_database_schema() -> list[str]:
    """Return missing tables required for Bridge and tenant onboarding."""
    try:
        table_names = set(inspect(engine).get_table_names())
    except SQLAlchemyError as exc:
        raise BridgeLaunchError(f"Database is not reachable: {exc}") from exc

    return [table for table in REQUIRED_SCHEMA_TABLES if table not in table_names]


def verify_database_connection(db: Session) -> None:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise BridgeLaunchError(f"Database connection check failed: {exc}") from exc


def count_platform_operators(db: Session) -> int:
    return (
        db.query(User)
        .filter(
            User.role == USER_ROLE_PLATFORM_SUPER_ADMIN,
            User.agency_id.is_(None),
            User.is_active.is_(True),
        )
        .count()
    )


def bootstrap_platform_operator(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    force_password_reset: bool = False,
) -> tuple[User, bool]:
    """Create or reconcile the bootstrap platform operator. Never seeds tenant agencies."""
    normalized_username = username.strip()
    normalized_email = email.strip().lower()
    if not normalized_username:
        raise BridgeLaunchError("Bridge launch requires a platform operator username.")
    if not normalized_email:
        raise BridgeLaunchError("Bridge launch requires a platform operator email.")
    if not password.strip():
        raise BridgeLaunchError("Bridge launch requires a platform operator password.")

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        raise BridgeLaunchError(str(exc)) from exc

    existing_operator = (
        db.query(User)
        .filter(
            User.role == USER_ROLE_PLATFORM_SUPER_ADMIN,
            User.agency_id.is_(None),
        )
        .order_by(User.id.asc())
        .first()
    )
    user_by_username = db.query(User).filter(User.username == normalized_username).first()

    if user_by_username is not None:
        if (
            user_by_username.role != USER_ROLE_PLATFORM_SUPER_ADMIN
            or user_by_username.agency_id is not None
        ):
            raise BridgeLaunchError(
                f"Username '{normalized_username}' is already assigned to a tenant CRM account."
            )

        updated = False
        if user_by_username.email != normalized_email:
            user_by_username.email = normalized_email
            updated = True
        if force_password_reset or updated:
            user_by_username.password_hash = password_hash
            updated = True
        if not user_by_username.is_active:
            user_by_username.is_active = True
            updated = True
        if updated:
            db.commit()
            db.refresh(user_by_username)
        return user_by_username, False

    if existing_operator is not None:
        raise BridgeLaunchError(
            "A platform operator already exists. "
            f"Sign in to The Bridge as '{existing_operator.username}' or rerun launch with that username."
        )

    user = User(
        agency_id=None,
        username=normalized_username,
        email=normalized_email,
        password_hash=password_hash,
        role=USER_ROLE_PLATFORM_SUPER_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, True


def run_bridge_launch(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    force_password_reset: bool = False,
    check_only: bool = False,
    public_registration_enabled: bool,
) -> BridgeLaunchReport:
    missing_tables = verify_database_schema()
    if missing_tables:
        raise BridgeLaunchError(
            "Database schema is incomplete. Missing tables: "
            + ", ".join(missing_tables)
            + ". Apply db/init.sql on fresh volumes or run incremental migrations from db/MIGRATION_ORDER.txt."
        )

    verify_database_connection(db)

    if check_only:
        return BridgeLaunchReport(
            schema_ready=True,
            platform_operator_username=username.strip(),
            platform_operator_created=False,
            platform_operator_count=count_platform_operators(db),
            public_registration_enabled=public_registration_enabled,
        )

    user, created = bootstrap_platform_operator(
        db,
        username=username,
        email=email,
        password=password,
        force_password_reset=force_password_reset,
    )

    return BridgeLaunchReport(
        schema_ready=True,
        platform_operator_username=user.username,
        platform_operator_created=created,
        platform_operator_count=count_platform_operators(db),
        public_registration_enabled=public_registration_enabled,
    )
