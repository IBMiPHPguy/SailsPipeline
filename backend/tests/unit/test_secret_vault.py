from cryptography.fernet import Fernet

from app.secret_vault import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_secret_round_trip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.secret_vault.settings.resolve_cc_auth_encryption_key", lambda: key)

    encrypted = encrypt_secret("tenant-gemini-key-abcdefghijklmnopqrst")
    assert "tenant-gemini-key" not in encrypted
    assert decrypt_secret(encrypted) == "tenant-gemini-key-abcdefghijklmnopqrst"
