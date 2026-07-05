import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.gemini_service import GeminiConfigurationError
from app.services.agency_settings_service import get_agency_settings_row
from app.services.gemini_config_service import (
    AGENCY_OWNER_AI_SETUP_MESSAGE,
    clear_agency_gemini_api_key,
    is_gemini_configured,
    resolve_gemini_credentials,
    save_agency_gemini_api_key,
    uses_tenant_gemini_api_key,
)
from app.tenant_constants import DEFAULT_AGENCY_ID


@pytest.fixture
def production_gemini_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "cc_auth_encryption_key", Fernet.generate_key().decode())


def test_uses_tenant_gemini_api_key_only_outside_development(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    assert uses_tenant_gemini_api_key() is False

    monkeypatch.setattr(settings, "app_env", "production")
    assert uses_tenant_gemini_api_key() is True


def test_resolve_gemini_credentials_uses_env_key_in_development(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "gemini_api_key", "dev-gemini-key-1234567890")

    api_key, model_name = resolve_gemini_credentials(None, agency_id=DEFAULT_AGENCY_ID)
    assert api_key == "dev-gemini-key-1234567890"
    assert model_name == settings.gemini_model


def test_resolve_gemini_credentials_requires_tenant_key_in_production(db, production_gemini_env):
    with pytest.raises(GeminiConfigurationError, match=AGENCY_OWNER_AI_SETUP_MESSAGE):
        resolve_gemini_credentials(db, agency_id=DEFAULT_AGENCY_ID)


def test_save_and_resolve_agency_gemini_api_key(db, production_gemini_env):
    save_agency_gemini_api_key(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        api_key="tenant-gemini-key-abcdefghijklmnopqrst",
    )

    row = get_agency_settings_row(db, agency_id=DEFAULT_AGENCY_ID)
    assert row.encrypted_gemini_api_key
    assert "tenant-gemini-key" not in row.encrypted_gemini_api_key

    api_key, _model_name = resolve_gemini_credentials(db, agency_id=DEFAULT_AGENCY_ID)
    assert api_key == "tenant-gemini-key-abcdefghijklmnopqrst"
    assert is_gemini_configured(db, agency_id=DEFAULT_AGENCY_ID) is True

    clear_agency_gemini_api_key(db, agency_id=DEFAULT_AGENCY_ID)
    assert is_gemini_configured(db, agency_id=DEFAULT_AGENCY_ID) is False
