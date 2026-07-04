from datetime import timedelta

import pytest

from app.models import Agency
from app.services.subscription_service import (
    LOCK_REASON_TRIAL_EXPIRED,
    compute_trial_ends_at,
    enforce_trial_expiration,
    is_trial_expired,
    is_trial_expired_lock,
    lock_expired_trials,
    resolve_subscription_lock_reason,
    utc_now,
)
from app.tenant_roles import SUBSCRIPTION_STATE_LOCKED, SUBSCRIPTION_STATE_TRIALING


def test_compute_trial_ends_at_defaults_to_seven_days():
    starts_at = utc_now()
    ends_at = compute_trial_ends_at(starts_at=starts_at)
    assert ends_at - starts_at == timedelta(days=7)


def test_enforce_trial_expiration_locks_expired_trialing_agency(db):
    agency = Agency(
        id="trial-agency-0001",
        name="Trial Agency",
        slug="trial-agency",
        organization_handle="trial-agency",
        subscription_state=SUBSCRIPTION_STATE_TRIALING,
        trial_ends_at=utc_now() - timedelta(minutes=1),
        is_active=True,
    )
    db.add(agency)
    db.commit()

    locked = enforce_trial_expiration(db, agency)
    db.refresh(agency)

    assert locked is True
    assert agency.subscription_state == SUBSCRIPTION_STATE_LOCKED
    assert resolve_subscription_lock_reason(agency) == LOCK_REASON_TRIAL_EXPIRED
    assert is_trial_expired_lock(agency) is True


def test_lock_expired_trials_batch_locks_due_workspaces(db):
    agency = Agency(
        id="trial-agency-0002",
        name="Expired Trial",
        slug="expired-trial",
        organization_handle="expired-trial",
        subscription_state=SUBSCRIPTION_STATE_TRIALING,
        trial_ends_at=utc_now() - timedelta(hours=1),
        is_active=True,
    )
    db.add(agency)
    db.commit()

    locked_count = lock_expired_trials(db)
    db.refresh(agency)

    assert locked_count == 1
    assert agency.subscription_state == SUBSCRIPTION_STATE_LOCKED


def test_active_trialing_agency_is_not_expired(db):
    agency = Agency(
        id="trial-agency-0003",
        name="Active Trial",
        slug="active-trial",
        organization_handle="active-trial",
        subscription_state=SUBSCRIPTION_STATE_TRIALING,
        trial_ends_at=utc_now() + timedelta(days=2),
        is_active=True,
    )
    db.add(agency)
    db.commit()

    assert is_trial_expired(agency) is False
    assert enforce_trial_expiration(db, agency) is False
