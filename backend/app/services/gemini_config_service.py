from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.email_config import APP_ENV_DEVELOPMENT, APP_ENV_TEST
from app.gemini_service import GeminiConfigurationError
from app.models import AgencySettings
from app.secret_vault import decrypt_secret, encrypt_secret
from app.services.agency_settings_service import get_agency_settings_row

GEMINI_API_KEY_MIN_LENGTH = 20

AGENCY_OWNER_AI_SETUP_MESSAGE = (
    "AI is not configured for your agency. Ask your agency owner to add a Gemini API key "
    "in Agency Settings to enable AI features."
)

DEV_ENV_AI_SETUP_MESSAGE = "Gemini is not configured. Add GEMINI_API_KEY to your environment."


def uses_tenant_gemini_api_key() -> bool:
    return settings.app_env not in {APP_ENV_DEVELOPMENT, APP_ENV_TEST}


def gemini_configuration_detail(*, can_manage: bool) -> str:
    if uses_tenant_gemini_api_key():
        if can_manage:
            return (
                "AI is not configured for your agency. Add a Gemini API key in Agency Settings "
                "to enable AI features."
            )
        return AGENCY_OWNER_AI_SETUP_MESSAGE
    return DEV_ENV_AI_SETUP_MESSAGE


def agency_has_gemini_api_key(row: AgencySettings) -> bool:
    return bool((row.encrypted_gemini_api_key or "").strip())


def is_gemini_configured(db: Session, *, agency_id: str) -> bool:
    if not uses_tenant_gemini_api_key():
        return bool((settings.gemini_api_key or "").strip())

    row = get_agency_settings_row(db, agency_id=agency_id)
    return agency_has_gemini_api_key(row)


def resolve_gemini_credentials(db: Session, *, agency_id: str) -> tuple[str, str]:
    if not uses_tenant_gemini_api_key():
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            raise GeminiConfigurationError(DEV_ENV_AI_SETUP_MESSAGE)
        return api_key, settings.gemini_model

    row = get_agency_settings_row(db, agency_id=agency_id)
    encrypted = (row.encrypted_gemini_api_key or "").strip()
    if not encrypted:
        raise GeminiConfigurationError(AGENCY_OWNER_AI_SETUP_MESSAGE)

    api_key = decrypt_secret(encrypted).strip()
    if not api_key:
        raise GeminiConfigurationError(AGENCY_OWNER_AI_SETUP_MESSAGE)
    return api_key, settings.gemini_model


def save_agency_gemini_api_key(db: Session, *, agency_id: str, api_key: str) -> AgencySettings:
    normalized = api_key.strip()
    if len(normalized) < GEMINI_API_KEY_MIN_LENGTH:
        raise ValueError("Gemini API key looks too short. Paste the full key from Google AI Studio.")

    row = get_agency_settings_row(db, agency_id=agency_id)
    row.encrypted_gemini_api_key = encrypt_secret(normalized)
    db.commit()
    db.refresh(row)
    return row


def clear_agency_gemini_api_key(db: Session, *, agency_id: str) -> AgencySettings:
    row = get_agency_settings_row(db, agency_id=agency_id)
    row.encrypted_gemini_api_key = None
    db.commit()
    db.refresh(row)
    return row
