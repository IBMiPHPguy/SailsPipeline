from __future__ import annotations

import json
import re
import secrets
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings

_CARD_PAYLOAD_KEYS = frozenset({"cardholder_name", "card_number", "expiration", "security_code"})


def _require_fernet() -> Fernet:
    try:
        raw_key = settings.resolve_cc_auth_encryption_key()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Card vault encryption is not configured on the server.",
        ) from exc
    try:
        return Fernet(raw_key.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Card vault encryption key is invalid.",
        ) from exc


def verify_vault_access_key(candidate: str) -> None:
    try:
        expected = settings.resolve_cc_auth_vault_access_key()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Card vault access is not configured on the server.",
        ) from exc
    if not secrets.compare_digest(candidate.strip(), expected):
        raise HTTPException(status_code=403, detail="Invalid vault access key.")


def normalize_card_number(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) < 13 or len(digits) > 19:
        raise HTTPException(status_code=400, detail="Enter a valid card number.")
    return digits


def normalize_expiration(value: str) -> str:
    stripped = (value or "").strip()
    match = re.fullmatch(r"(\d{2})\s*/\s*(\d{2})", stripped)
    if not match:
        raise HTTPException(status_code=400, detail="Expiration must use MM/YY format.")
    month = int(match.group(1))
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Expiration month must be between 01 and 12.")
    return f"{match.group(1)}/{match.group(2)}"


def normalize_security_code(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) not in {3, 4}:
        raise HTTPException(status_code=400, detail="Security code must be 3 or 4 digits.")
    return digits


def normalize_card_payload(raw: dict[str, Any]) -> dict[str, str]:
    cardholder_name = str(raw.get("cardholder_name", "")).strip()
    if len(cardholder_name) < 2:
        raise HTTPException(status_code=400, detail="Cardholder name is required.")

    return {
        "cardholder_name": cardholder_name,
        "card_number": normalize_card_number(str(raw.get("card_number", ""))),
        "expiration": normalize_expiration(str(raw.get("expiration", ""))),
        "security_code": normalize_security_code(str(raw.get("security_code", ""))),
    }


def encrypt_card_payload(payload: dict[str, str]) -> str:
    missing = _CARD_PAYLOAD_KEYS.difference(payload)
    if missing:
        raise HTTPException(status_code=400, detail="Complete card details are required.")
    token = _require_fernet()
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return token.encrypt(serialized.encode("utf-8")).decode("utf-8")


def decrypt_card_payload(encrypted_value: str) -> dict[str, str]:
    token = _require_fernet()
    try:
        decrypted = token.decrypt(encrypted_value.encode("utf-8"))
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Unable to decrypt stored card data.") from exc

    payload = json.loads(decrypted.decode("utf-8"))
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Stored card data is corrupted.")
    return {key: str(payload.get(key, "")) for key in _CARD_PAYLOAD_KEYS}
