from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

APP_ENV_DEVELOPMENT = "development"
APP_ENV_STAGING = "staging"
APP_ENV_PRODUCTION = "production"
APP_ENV_TEST = "test"

DEPLOYMENT_APP_ENVS = frozenset({APP_ENV_DEVELOPMENT, APP_ENV_STAGING, APP_ENV_PRODUCTION})
INTERNAL_APP_ENVS = frozenset({APP_ENV_TEST})
ALLOWED_APP_ENVS = DEPLOYMENT_APP_ENVS | INTERNAL_APP_ENVS

APP_ENV_ALIASES = {"prod": APP_ENV_PRODUCTION}

EmailBackend = Literal["smtp", "api"]

DEVELOPMENT_MAILPIT_HOST = "mailpit"
DEVELOPMENT_MAILPIT_PORT = 1025
ALLOWED_DEVELOPMENT_SMTP_HOSTS = frozenset({DEVELOPMENT_MAILPIT_HOST, "localhost", "127.0.0.1"})


class DevelopmentEmailIsolationError(RuntimeError):
    """Raised when development mode would route mail outside the local sandbox."""


@dataclass(frozen=True)
class EmailDeliverySettings:
    """Resolved email transport settings for the active deployment tier."""

    environment: str
    backend: EmailBackend
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    from_address: str
    api_key: str | None
    api_provider: str


class _EmailSettingsSource(Protocol):
    app_env: str
    email_from_address: str
    email_from_address_staging: str | None
    email_api_provider: str
    email_api_key: str | None
    email_api_key_staging: str | None


def resolve_email_delivery_settings(settings: _EmailSettingsSource) -> EmailDeliverySettings:
    """Derive email routing from APP_ENV. Development always uses local Mailpit SMTP."""
    env = settings.app_env

    if env in {APP_ENV_DEVELOPMENT, APP_ENV_TEST}:
        return EmailDeliverySettings(
            environment=env,
            backend="smtp",
            smtp_host=DEVELOPMENT_MAILPIT_HOST,
            smtp_port=DEVELOPMENT_MAILPIT_PORT,
            smtp_username="",
            smtp_password="",
            smtp_use_tls=False,
            from_address=settings.email_from_address,
            api_key=None,
            api_provider=settings.email_api_provider,
        )

    if env == APP_ENV_STAGING:
        # Cloud sandbox tier: Resend/Postmark (or similar) with staging-only credentials.
        if not settings.email_api_key_staging:
            raise RuntimeError(
                "EMAIL_API_KEY_STAGING is required when APP_ENV=staging. "
                "Configure a provider sandbox key before sending mail."
            )
        return EmailDeliverySettings(
            environment=env,
            backend="api",
            smtp_host="",
            smtp_port=0,
            smtp_username="",
            smtp_password="",
            smtp_use_tls=False,
            from_address=settings.email_from_address_staging or settings.email_from_address,
            api_key=settings.email_api_key_staging,
            api_provider=settings.email_api_provider,
        )

    if env == APP_ENV_PRODUCTION:
        if not settings.email_api_key:
            raise RuntimeError(
                "EMAIL_API_KEY is required when APP_ENV=production. "
                "Refusing to start email delivery without live provider credentials."
            )
        return EmailDeliverySettings(
            environment=env,
            backend="api",
            smtp_host="",
            smtp_port=0,
            smtp_username="",
            smtp_password="",
            smtp_use_tls=False,
            from_address=settings.email_from_address,
            api_key=settings.email_api_key,
            api_provider=settings.email_api_provider,
        )

    raise RuntimeError(f"Unsupported APP_ENV for email delivery: {env}")
