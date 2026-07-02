from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.cc_auth_vault import (
    decrypt_card_payload,
    encrypt_card_payload,
    normalize_card_payload,
    verify_vault_access_key,
)
from app.config import DEFAULT_DEV_CC_AUTH_VAULT_ACCESS_KEY, Settings
from app.schemas import CcAuthCardPayload


SAMPLE_CARD_PAYLOAD = {
    "cardholder_name": "Jane Cruise",
    "card_number": "4111111111111111",
    "expiration": "12/30",
    "security_code": "123",
}


@pytest.fixture
def vault_encryption_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.cc_auth_vault.settings.cc_auth_encryption_key", key)
    monkeypatch.setattr("app.cc_auth_vault.settings.cc_auth_vault_access_key", "unit-test-vault-key")
    return key


def test_encrypt_decrypt_round_trip(vault_encryption_key):
    encrypted = encrypt_card_payload(SAMPLE_CARD_PAYLOAD)
    assert SAMPLE_CARD_PAYLOAD["card_number"] not in encrypted
    decrypted = decrypt_card_payload(encrypted)
    assert decrypted == SAMPLE_CARD_PAYLOAD


def test_normalize_card_payload_strips_and_formats():
    normalized = normalize_card_payload(
        {
            "cardholder_name": "  Jane Cruise  ",
            "card_number": "4111 1111 1111 1111",
            "expiration": "12 / 30",
            "security_code": "123",
        }
    )
    assert normalized["card_number"] == "4111111111111111"
    assert normalized["expiration"] == "12/30"


def test_normalize_card_payload_rejects_invalid_pan():
    with pytest.raises(HTTPException) as exc:
        normalize_card_payload({**SAMPLE_CARD_PAYLOAD, "card_number": "1234"})
    assert exc.value.status_code == 400


def test_normalize_card_payload_rejects_invalid_expiration():
    with pytest.raises(HTTPException) as exc:
        normalize_card_payload({**SAMPLE_CARD_PAYLOAD, "expiration": "13/30"})
    assert exc.value.status_code == 400


def test_verify_vault_access_key_accepts_matching_key(vault_encryption_key):
    verify_vault_access_key("unit-test-vault-key")


def test_verify_vault_access_key_rejects_wrong_key(vault_encryption_key):
    with pytest.raises(HTTPException) as exc:
        verify_vault_access_key("wrong-key")
    assert exc.value.status_code == 403


def test_verify_vault_access_key_uses_dev_fallback_when_unset(monkeypatch):
    settings = Settings(
        app_env="development",
        cc_auth_encryption_key=Fernet.generate_key().decode(),
        cc_auth_vault_access_key=None,
    )
    monkeypatch.setattr("app.cc_auth_vault.settings", settings)
    verify_vault_access_key(DEFAULT_DEV_CC_AUTH_VAULT_ACCESS_KEY)


def test_verify_vault_access_key_requires_production_configuration(monkeypatch):
    settings = Settings(
        app_env="production",
        jwt_secret="x" * 32,
        cc_auth_encryption_key=Fernet.generate_key().decode(),
        cc_auth_vault_access_key=None,
    )
    monkeypatch.setattr("app.cc_auth_vault.settings", settings)
    with pytest.raises(HTTPException) as exc:
        verify_vault_access_key("anything")
    assert exc.value.status_code == 503


def test_settings_empty_vault_access_key_treated_as_unset():
    settings = Settings(app_env="development", cc_auth_vault_access_key="   ")
    assert settings.cc_auth_vault_access_key is None
    assert settings.resolve_cc_auth_vault_access_key() == DEFAULT_DEV_CC_AUTH_VAULT_ACCESS_KEY


def test_settings_resolve_encryption_key_dev_derivation():
    settings = Settings(app_env="development", jwt_secret="test-jwt-secret", cc_auth_encryption_key=None)
    key = settings.resolve_cc_auth_encryption_key()
    assert key
    assert settings.resolve_cc_auth_encryption_key() == key


def test_cc_auth_card_payload_schema_normalizes_inputs():
    payload = CcAuthCardPayload(
        cardholder_name="  Jane Cruise ",
        card_number="4111-1111-1111-1111",
        expiration="12/30",
        security_code="123",
    )
    assert payload.card_number == "4111111111111111"
    assert payload.cardholder_name == "Jane Cruise"


def test_cc_auth_card_payload_schema_rejects_short_security_code():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CcAuthCardPayload(
            cardholder_name="Jane Cruise",
            card_number="4111111111111111",
            expiration="12/30",
            security_code="12",
        )
