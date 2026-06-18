from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.attachment_storage import migrate_legacy_attachment_content
from app.config import settings
from app.database import Base, SessionLocal, engine


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
    application = FastAPI(
        title="CruiseTravelNow API",
        description="Workflow API for new cruise travel requests.",
        version="0.3.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.routers import register_routers

    register_routers(application)

    return application


app = create_app()
