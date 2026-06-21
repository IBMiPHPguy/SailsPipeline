from datetime import UTC, datetime, timedelta

import pytest

from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_password,
    verify_password,
)


def test_validate_password_rejects_invalid_values():
    with pytest.raises(ValueError, match="spaces"):
        validate_password("Has Space1!")
    with pytest.raises(ValueError, match="more than 10"):
        validate_password("Short1!")
    with pytest.raises(ValueError, match="uppercase"):
        validate_password("alllowercase1!")


def test_hash_and_verify_password():
    hashed = hash_password("ValidPass1!")
    assert hashed != "ValidPass1!"
    assert verify_password("ValidPass1!", hashed) is True
    assert verify_password("WrongPass1!", hashed) is False


def test_create_and_decode_access_token():
    from app.tenant_constants import DEFAULT_AGENCY_ID
    from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER

    token = create_access_token(
        user_id=42,
        username="agent-one",
        agency_id=DEFAULT_AGENCY_ID,
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    claims = decode_access_token(token)
    assert claims.username == "agent-one"
    assert claims.user_id == 42
    assert claims.agency_id == DEFAULT_AGENCY_ID
    assert claims.role == USER_ROLE_TENANT_SUPER_USER


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token("not-a-valid-token")


def test_decode_access_token_rejects_missing_subject():
    from jose import jwt

    from app.config import settings

    token = jwt.encode({"exp": datetime.now(UTC) + timedelta(minutes=5)}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with pytest.raises(ValueError, match="Invalid or expired"):
        decode_access_token(token)
