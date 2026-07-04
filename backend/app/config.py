from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.email_config import (
    ALLOWED_APP_ENVS,
    APP_ENV_ALIASES,
    APP_ENV_DEVELOPMENT,
    APP_ENV_PRODUCTION,
    APP_ENV_STAGING,
    DEPLOYMENT_APP_ENVS,
    EmailDeliverySettings,
    resolve_email_delivery_settings,
)

DEFAULT_DEV_CC_AUTH_VAULT_ACCESS_KEY = "dev-vault-access-change-me"


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://cruiseapp:cruisesecret@db:3306/sailspipeline"
    app_env: str = APP_ENV_DEVELOPMENT
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
    trial_period_days: int = 7
    trial_scheduler_enabled: bool = True
    trial_scheduler_poll_seconds: int = 300
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
    # Legacy overrides (ignored when APP_ENV=development; routing is tier-driven).
    email_backend: str = "smtp"
    email_host: str = "mailpit"
    email_port: int = 1025
    email_username: str = ""
    email_password: str = ""
    email_use_tls: bool = False
    email_from_address: str = "notifications@sailspipeline.com"
    email_from_address_staging: str | None = None
    email_api_provider: str = "resend"
    email_api_key: str | None = None
    email_api_key_staging: str | None = None
    cc_auth_portal_base_url: str = "http://localhost:5173/cc-auth"
    terms_portal_base_url: str = "http://localhost:5173/accept-terms"
    insurance_portal_base_url: str = "http://localhost:5173/insurance-auth"
    cc_auth_encryption_key: str | None = None
    cc_auth_vault_access_key: str | None = None
    brand_uploads_dir: str = "static/uploads"
    s3_brand_bucket: str | None = None
    s3_brand_region: str = "us-east-1"
    s3_brand_public_base_url: str | None = None
    public_app_base_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("app_env", mode="before")
    @classmethod
    def validate_app_env(cls, value: object) -> str:
        normalized = str(value).strip().lower()
        normalized = APP_ENV_ALIASES.get(normalized, normalized)
        if normalized not in ALLOWED_APP_ENVS:
            allowed = ", ".join(sorted(DEPLOYMENT_APP_ENVS))
            raise ValueError(f"APP_ENV must be one of: {allowed}")
        return normalized

    @field_validator(
        "allow_public_registration",
        "expose_openapi",
        "rollup_scheduler_enabled",
        "trial_scheduler_enabled",
        "email_use_tls",
        mode="before",
    )
    @classmethod
    def parse_bool(cls, value):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return value

    @field_validator("cc_auth_encryption_key", "cc_auth_vault_access_key", mode="before")
    @classmethod
    def empty_optional_secret_to_none(cls, value: object) -> object:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return origins or ["http://localhost:8080"]

    @property
    def rate_limiting_enabled(self) -> bool:
        return self.app_env not in {"test"}

    @property
    def is_development(self) -> bool:
        return self.app_env == APP_ENV_DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        return self.app_env == APP_ENV_STAGING

    @property
    def is_production(self) -> bool:
        return self.app_env == APP_ENV_PRODUCTION

    @property
    def ENVIRONMENT(self) -> str:
        """Deployment tier alias used by asset upload modules (dev | stage | prod)."""
        if self.is_development or self.app_env == "test":
            return "dev"
        if self.is_staging:
            return "stage"
        return "prod"

    @property
    def uses_local_brand_uploads(self) -> bool:
        return self.ENVIRONMENT == "dev"

    def resolve_email_delivery_settings(self) -> EmailDeliverySettings:
        return resolve_email_delivery_settings(self)

    def resolve_cc_auth_encryption_key(self) -> str:
        if self.cc_auth_encryption_key and self.cc_auth_encryption_key.strip():
            return self.cc_auth_encryption_key.strip()
        if self.app_env in {APP_ENV_DEVELOPMENT, "test"}:
            import base64
            import hashlib

            digest = hashlib.sha256(f"{self.jwt_secret}:sailspipeline-cc-auth-vault".encode()).digest()
            return base64.urlsafe_b64encode(digest).decode()
        raise ValueError("CC_AUTH_ENCRYPTION_KEY must be set for card vault encryption.")

    def resolve_cc_auth_vault_access_key(self) -> str:
        if self.cc_auth_vault_access_key and self.cc_auth_vault_access_key.strip():
            return self.cc_auth_vault_access_key.strip()
        if self.app_env in {APP_ENV_DEVELOPMENT, "test"}:
            return DEFAULT_DEV_CC_AUTH_VAULT_ACCESS_KEY
        raise ValueError("CC_AUTH_VAULT_ACCESS_KEY must be set for card vault access.")


settings = Settings()
