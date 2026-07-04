from datetime import timedelta

import pytest

from app.database import SessionLocal
from app.models import Agency, User
from app.security import create_access_token, hash_password
from app.services.subscription_service import utc_now
from app.tenant_roles import SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_TRIALING, USER_ROLE_TENANT_SUPER_USER

LOGIN_PASSWORD = "AgencyPass1!"


@pytest.fixture
def expired_trial_agency(db):
    agency = Agency(
        id="expired-trial-agency-01",
        name="Expired Demo Travel",
        slug="expired-demo",
        organization_handle="expired-demo",
        subscription_state=SUBSCRIPTION_STATE_TRIALING,
        trial_ends_at=utc_now() - timedelta(minutes=5),
        is_active=True,
    )
    user = User(
        agency_id=agency.id,
        username="demo.owner",
        email="owner@expireddemo.example",
        password_hash=hash_password(LOGIN_PASSWORD),
        role=USER_ROLE_TENANT_SUPER_USER,
    )
    db.add(agency)
    db.add(user)
    db.commit()
    db.refresh(agency)
    db.refresh(user)
    return agency, user


@pytest.mark.integration
def test_login_blocks_expired_trial_with_demo_message(client, expired_trial_agency):
    agency, user = expired_trial_agency

    response = client.post(
        "/api/auth/login",
        json={
            "organization_handle": agency.organization_handle,
            "username": user.username,
            "password": LOGIN_PASSWORD,
        },
    )

    assert response.status_code == 403, response.text
    payload = response.json()
    assert payload["detail"]["lock_reason"] == "trial_expired"
    assert "demo has ended" in payload["detail"]["message"].lower()

    db = SessionLocal()
    try:
        refreshed = db.get(Agency, agency.id)
        assert refreshed.subscription_state == SUBSCRIPTION_STATE_LOCKED
    finally:
        db.close()


@pytest.mark.integration
def test_subscription_gatekeeper_returns_trial_reason_for_locked_demo(client, expired_trial_agency, db):
    agency, user = expired_trial_agency
    agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()

    token = create_access_token(
        user_id=user.id,
        username=user.username,
        agency_id=user.agency_id,
        role=user.role,
    )

    response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 402, response.text
    payload = response.json()
    assert payload["subscription_state"] == SUBSCRIPTION_STATE_LOCKED
    assert payload["lock_reason"] == "trial_expired"
    assert "demo has ended" in payload["detail"].lower()
