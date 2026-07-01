import pytest

from app.config import Settings
from app.email_config import (
    APP_ENV_DEVELOPMENT,
    APP_ENV_PRODUCTION,
    APP_ENV_STAGING,
    DEVELOPMENT_MAILPIT_HOST,
    DEVELOPMENT_MAILPIT_PORT,
    resolve_email_delivery_settings,
)

def test_resolve_email_delivery_settings_for_development_ignores_cloud_keys():
    settings = Settings(
        app_env=APP_ENV_DEVELOPMENT,
        email_backend="api",
        email_host="smtp.sendgrid.net",
        email_port=587,
        email_api_key="live-secret-key",
        email_api_key_staging="staging-secret-key",
    )

    delivery = resolve_email_delivery_settings(settings)

    assert delivery.backend == "smtp"
    assert delivery.smtp_host == DEVELOPMENT_MAILPIT_HOST
    assert delivery.smtp_port == DEVELOPMENT_MAILPIT_PORT
    assert delivery.api_key is None


def test_resolve_email_delivery_settings_for_staging_requires_sandbox_key():
    settings = Settings(app_env=APP_ENV_STAGING, email_api_key_staging=None)

    with pytest.raises(RuntimeError, match="EMAIL_API_KEY_STAGING"):
        resolve_email_delivery_settings(settings)


def test_resolve_email_delivery_settings_for_staging_uses_api_backend():
    settings = Settings(
        app_env=APP_ENV_STAGING,
        email_api_key_staging="re_staging_test",
        email_from_address_staging="staging@mail.sailspipeline.com",
    )

    delivery = resolve_email_delivery_settings(settings)

    assert delivery.backend == "api"
    assert delivery.api_key == "re_staging_test"
    assert delivery.from_address == "staging@mail.sailspipeline.com"


def test_resolve_email_delivery_settings_for_production_requires_live_key():
    settings = Settings(app_env=APP_ENV_PRODUCTION, email_api_key=None)

    with pytest.raises(RuntimeError, match="EMAIL_API_KEY"):
        resolve_email_delivery_settings(settings)


def test_settings_rejects_invalid_app_env():
    with pytest.raises(ValueError, match="APP_ENV must be one of"):
        Settings(app_env="local")
