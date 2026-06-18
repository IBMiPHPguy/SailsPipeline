from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.attachment_storage import migrate_legacy_attachment_content
from app.branding import API_TITLE
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.rate_limit import limiter
from app.security_config import validate_production_settings


def seed_admin_user(db) -> None:
    from app.models import User
    from app.security import hash_password

    if not settings.seed_admin_username or not settings.seed_admin_password:
        return

    email = settings.seed_admin_email or f"{settings.seed_admin_username}@example.com"
    existing = db.query(User).filter(User.username == settings.seed_admin_username).first()
    if existing:
        if existing.email != email:
            existing.email = email
            db.commit()
        return

    user = User(
        username=settings.seed_admin_username,
        email=email,
        password_hash=hash_password(settings.seed_admin_password),
    )
    db.add(user)
    db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.app_env != "test":
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.app_env != "test":
            seed_admin_user(db)
            migrate_legacy_attachment_content(db, settings.attachments_dir)
    finally:
        db.close()
    yield


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
