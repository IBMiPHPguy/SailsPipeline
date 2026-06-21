import pytest

from app.security import hash_password
from app.services.auth_service import authenticate_platform_operator
from app.tenant_roles import USER_ROLE_PLATFORM_SUPER_ADMIN


def test_authenticate_platform_operator_ignores_tenant_membership(db):
    from app.models import User

    user = User(
        agency_id=None,
        username="platform-op",
        email="platform-op@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_PLATFORM_SUPER_ADMIN,
    )
    db.add(user)
    db.commit()

    authenticated = authenticate_platform_operator(
        db,
        username="platform-op",
        password="ValidPass1!",
    )
    assert authenticated is not None
    assert authenticated.agency_id is None


def test_authenticate_platform_operator_rejects_tenant_bound_account(db, test_user):
    assert (
        authenticate_platform_operator(
            db,
            username=test_user.username,
            password="TestPassword1!",
        )
        is None
    )
