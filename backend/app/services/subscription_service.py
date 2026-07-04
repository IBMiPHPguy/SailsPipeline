from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Agency
from app.tenant_roles import (
    SUBSCRIPTION_STATE_LOCKED,
    SUBSCRIPTION_STATE_PAST_DUE,
    SUBSCRIPTION_STATE_TRIALING,
)

LOCK_REASON_TRIAL_EXPIRED = "trial_expired"

TRIAL_EXPIRED_LOGIN_MESSAGE = (
    "Your SailsPipeline demo has ended. Contact SailsPipeline to activate your account with a subscription."
)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


def compute_trial_ends_at(*, starts_at: datetime | None = None) -> datetime:
    start = normalize_datetime(starts_at or utc_now())
    return start + timedelta(days=settings.trial_period_days)


def is_trial_expired(agency: Agency, *, now: datetime | None = None) -> bool:
    if agency.trial_ends_at is None:
        return False
    current = normalize_datetime(now or utc_now())
    return normalize_datetime(agency.trial_ends_at) <= current


def is_trial_expired_lock(agency: Agency, *, now: datetime | None = None) -> bool:
    return (
        agency.subscription_state == SUBSCRIPTION_STATE_LOCKED
        and agency.trial_ends_at is not None
        and is_trial_expired(agency, now=now)
    )


def resolve_subscription_lock_reason(agency: Agency, *, now: datetime | None = None) -> str | None:
    if is_trial_expired_lock(agency, now=now):
        return LOCK_REASON_TRIAL_EXPIRED
    return None


def enforce_trial_expiration(db: Session, agency: Agency, *, now: datetime | None = None) -> bool:
    """Lock a trialing agency when its trial window ends. Returns True when newly locked."""
    if agency.subscription_state != SUBSCRIPTION_STATE_TRIALING:
        return False
    if not is_trial_expired(agency, now=now):
        return False

    agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()
    db.refresh(agency)
    return True


def lock_expired_trials(db: Session, *, now: datetime | None = None) -> int:
    current = normalize_datetime(now or utc_now())
    agencies = (
        db.query(Agency)
        .filter(
            Agency.subscription_state == SUBSCRIPTION_STATE_TRIALING,
            Agency.trial_ends_at.is_not(None),
            Agency.trial_ends_at <= current,
        )
        .all()
    )
    if not agencies:
        return 0

    for agency in agencies:
        agency.subscription_state = SUBSCRIPTION_STATE_LOCKED
    db.commit()
    return len(agencies)


def build_subscription_block_payload(agency: Agency, *, now: datetime | None = None) -> dict[str, str]:
    lock_reason = resolve_subscription_lock_reason(agency, now=now)
    payload = {
        "subscription_state": agency.subscription_state,
    }
    if lock_reason:
        payload["lock_reason"] = lock_reason
        payload["message"] = TRIAL_EXPIRED_LOGIN_MESSAGE
    elif agency.subscription_state == SUBSCRIPTION_STATE_PAST_DUE:
        payload["message"] = "Subscription payment required."
    else:
        payload["message"] = "Subscription payment required."
    return payload


def raise_if_login_blocked(db: Session, agency: Agency) -> None:
    enforce_trial_expiration(db, agency)
    db.refresh(agency)

    if agency.subscription_state == SUBSCRIPTION_STATE_LOCKED:
        lock_reason = resolve_subscription_lock_reason(agency)
        if lock_reason == LOCK_REASON_TRIAL_EXPIRED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": TRIAL_EXPIRED_LOGIN_MESSAGE,
                    "subscription_state": agency.subscription_state,
                    "lock_reason": lock_reason,
                },
            )

    if agency.subscription_state == SUBSCRIPTION_STATE_PAST_DUE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Your agency subscription payment is past due. CRM access is paused until billing is restored.",
                "subscription_state": agency.subscription_state,
            },
        )
