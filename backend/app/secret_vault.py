from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings


def _require_fernet() -> Fernet:
    try:
        raw_key = settings.resolve_cc_auth_encryption_key()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Server secret encryption is not configured.",
        ) from exc
    try:
        return Fernet(raw_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Server secret encryption key is invalid.",
        ) from exc


def encrypt_secret(plaintext: str) -> str:
    token = _require_fernet()
    return token.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    token = _require_fernet()
    try:
        decrypted = token.decrypt(ciphertext.encode("utf-8"))
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Unable to decrypt stored secret.") from exc
    return decrypted.decode("utf-8")
