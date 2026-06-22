from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://cruiseapp:cruisesecret@db:3306/sailspipeline"
    app_env: str = "development"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    seed_admin_username: str | None = None
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    seed_bridge_admin_username: str | None = None
    seed_bridge_admin_email: str | None = None
    seed_bridge_admin_password: str | None = None
    platform_invite_expire_days: int = 7
    agency_invite_expire_days: int = 3
    rollup_scheduler_enabled: bool = True
    rollup_refresh_poll_seconds: int = 30
    rollup_daily_refresh_hour_utc: int = 3
    attachments_dir: str = "/app/uploads"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    allow_public_registration: bool = True
    cors_origins: str = "http://localhost:8080,http://localhost:5173,http://127.0.0.1:8080"
    expose_openapi: bool = True
    auth_rate_limit: str = "10/minute"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("allow_public_registration", "expose_openapi", "rollup_scheduler_enabled", mode="before")
    @classmethod
    def parse_bool(cls, value):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["http://localhost:8080"]

    @property
    def rate_limiting_enabled(self) -> bool:
        return self.app_env not in {"test"}


settings = Settings()
