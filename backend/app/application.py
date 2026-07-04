from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.agency_rollup_scheduler import start_agency_rollup_scheduler, stop_agency_rollup_scheduler
from app.trial_scheduler import start_trial_scheduler, stop_trial_scheduler
from app.attachment_storage import migrate_legacy_attachment_content
from app.branding import API_TITLE
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.rate_limit import limiter
from app.schema_migrations import run_startup_schema_migrations
from app.security_config import validate_production_settings
from app.subscription_gatekeeper import SubscriptionGatekeeperMiddleware
from app.tenant_middleware import TenantContextMiddleware

STATIC_ROOT = Path(__file__).resolve().parent.parent / "static"
BRAND_UPLOADS_DIR = STATIC_ROOT / "uploads"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.app_env != "test":
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.app_env != "test":
            run_startup_schema_migrations(db)
            migrate_legacy_attachment_content(db, settings.attachments_dir)
    finally:
        db.close()
    start_agency_rollup_scheduler()
    start_trial_scheduler()
    yield
    stop_trial_scheduler()
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

    BRAND_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    application.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")

    return application


app = create_app()
