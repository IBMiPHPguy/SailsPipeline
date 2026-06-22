from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.agency_rollup_scheduler import start_agency_rollup_scheduler, stop_agency_rollup_scheduler
from app.attachment_storage import migrate_legacy_attachment_content
from app.branding import API_TITLE
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.rate_limit import limiter
from app.security_config import validate_production_settings
from app.subscription_gatekeeper import SubscriptionGatekeeperMiddleware
from app.tenant_middleware import TenantContextMiddleware
from app.tenant_session import configure_tenant_session

configure_tenant_session()


def seed_admin_user(db) -> None:
    from app.models import User
    from app.security import hash_password
    from app.services.agency_rollup_service import refresh_agency_rollups
    from app.services.agency_service import ensure_default_agency
    from app.tenant_constants import DEFAULT_AGENCY_ID
    from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER

    default_agency = ensure_default_agency(db)

    if settings.app_env != "test":
        try:
            refresh_agency_rollups(db, default_agency.id)
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "Initial agency rollup refresh skipped; apply db/migrate_multi_tenant_phase3_rollups.sql if needed."
            )
            db.rollback()

    if not settings.seed_admin_username or not settings.seed_admin_password:
        db.commit()
        return

    email = settings.seed_admin_email or f"{settings.seed_admin_username}@example.com"
    existing = db.query(User).filter(User.username == settings.seed_admin_username).first()
    if existing:
        if existing.email != email:
            existing.email = email
        if existing.agency_id != default_agency.id:
            existing.agency_id = default_agency.id
        if existing.role != USER_ROLE_TENANT_SUPER_USER:
            existing.role = USER_ROLE_TENANT_SUPER_USER
        db.commit()
        return

    user = User(
        agency_id=DEFAULT_AGENCY_ID,
        username=settings.seed_admin_username,
        email=email,
        password_hash=hash_password(settings.seed_admin_password),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(user)
    db.commit()


def seed_bridge_admin_user(db) -> None:
    import logging

    from sqlalchemy.exc import SQLAlchemyError

    from app.models import User
    from app.security import hash_password
    from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN

    logger = logging.getLogger(__name__)

    if not settings.seed_bridge_admin_username or not settings.seed_bridge_admin_password:
        return

    email = settings.seed_bridge_admin_email or f"{settings.seed_bridge_admin_username}@example.com"
    existing = db.query(User).filter(User.username == settings.seed_bridge_admin_username).first()
    try:
        if existing:
            if existing.email != email:
                existing.email = email
            existing.agency_id = None
            if existing.role != USER_ROLE_PLATFORM_SUPER_ADMIN:
                existing.role = USER_ROLE_PLATFORM_SUPER_ADMIN
            db.commit()
            return

        user = User(
            agency_id=None,
            username=settings.seed_bridge_admin_username,
            email=email,
            password_hash=hash_password(settings.seed_bridge_admin_password),
            role=USER_ROLE_PLATFORM_SUPER_ADMIN,
        )
        db.add(user)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.warning(
            "Bridge operator seed skipped. Apply db/migrate_platform_operator_null_agency.sql first: %s",
            exc,
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.app_env != "test":
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.app_env != "test":
            seed_admin_user(db)
            seed_bridge_admin_user(db)
            migrate_legacy_attachment_content(db, settings.attachments_dir)
    finally:
        db.close()
    start_agency_rollup_scheduler()
    yield
    stop_agency_rollup_scheduler()


def create_app() -> FastAPI:
    validate_production_settings(settings)

    application = FastAPI(
        title=API_TITLE,
        description="Workflow API for new cruise travel requests.",
        version="0.3.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.expose_openapi else None,
        redoc_url="/redoc" if settings.expose_openapi else None,
        openapi_url="/openapi.json" if settings.expose_openapi else None,
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(TenantContextMiddleware)
    application.add_middleware(SubscriptionGatekeeperMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    from app.routers import register_routers

    register_routers(application)

    return application


app = create_app()
