from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import (
    CC_AUTH_STATUS_COMPLETED,
    CC_AUTH_STATUS_EXPIRED,
    CC_AUTH_STATUS_PENDING,
    CC_AUTH_TTL_HOURS,
)
from app.models import CreditCardAuthorization, TravelRequest


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CCAuthService:
    """Secure transient token lifecycle for passenger credit card authorization."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_portal_url(self, token: str) -> str:
        base = settings.cc_auth_portal_base_url.rstrip("/") + "/"
        return urljoin(base, token)

    def _expire_pending_tokens(self, travel_request_id: int) -> None:
        now = _utcnow()
        pending = (
            self.db.query(CreditCardAuthorization)
            .filter(
                CreditCardAuthorization.travel_request_id == travel_request_id,
                CreditCardAuthorization.status == CC_AUTH_STATUS_PENDING,
            )
            .all()
        )
        for record in pending:
            record.status = CC_AUTH_STATUS_EXPIRED
            if record.completed_at is None:
                record.completed_at = None
        if pending:
            self.db.flush()

    async def create_auth_request(self, travel_request_id: int) -> str:
        request = self.db.get(TravelRequest, travel_request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Travel request not found.")

        self._expire_pending_tokens(travel_request_id)

        token = secrets.token_urlsafe(48)
        expires_at = _utcnow() + timedelta(hours=CC_AUTH_TTL_HOURS)
        record = CreditCardAuthorization(
            id=str(uuid.uuid4()),
            agency_id=request.agency_id,
            travel_request_id=travel_request_id,
            secure_token=token,
            status=CC_AUTH_STATUS_PENDING,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return self._build_portal_url(token)

    async def validate_token(self, token: str) -> dict:
        normalized = token.strip()
        if not normalized:
            return {"valid": False, "reason": "missing_token"}

        record = (
            self.db.query(CreditCardAuthorization)
            .filter(CreditCardAuthorization.secure_token == normalized)
            .first()
        )
        if record is None:
            return {"valid": False, "reason": "not_found"}

        now = _utcnow()
        if record.status != CC_AUTH_STATUS_PENDING:
            return {
                "valid": False,
                "reason": "invalid_status",
                "status": record.status,
                "travel_request_id": record.travel_request_id,
            }

        if record.expires_at <= now:
            record.status = CC_AUTH_STATUS_EXPIRED
            self.db.commit()
            return {
                "valid": False,
                "reason": "expired",
                "travel_request_id": record.travel_request_id,
                "expires_at": record.expires_at.isoformat(),
            }

        return {
            "valid": True,
            "travel_request_id": record.travel_request_id,
            "agency_id": record.agency_id,
            "authorization_id": record.id,
            "expires_at": record.expires_at.isoformat(),
            "status": record.status,
        }

    def _get_record_by_token(self, token: str) -> CreditCardAuthorization | None:
        normalized = token.strip()
        if not normalized:
            return None
        return (
            self.db.query(CreditCardAuthorization)
            .filter(CreditCardAuthorization.secure_token == normalized)
            .first()
        )

    async def complete_authorization(self, token: str, card_payload: dict[str, str]) -> dict:
        from app.cc_auth_vault import encrypt_card_payload, normalize_card_payload

        validation = await self.validate_token(token)
        if not validation.get("valid"):
            reason = validation.get("reason", "invalid_token")
            detail = {
                "missing_token": "Authorization token is required.",
                "not_found": "Authorization link was not found.",
                "expired": "This authorization link has expired.",
                "invalid_status": "This authorization link is no longer active.",
            }.get(reason, "Authorization link is not valid.")
            raise HTTPException(status_code=410, detail=detail)

        record = self._get_record_by_token(token)
        if record is None:
            raise HTTPException(status_code=404, detail="Authorization link was not found.")

        normalized = normalize_card_payload(card_payload)
        encrypted = encrypt_card_payload(normalized)

        completed_at = _utcnow()
        record.status = CC_AUTH_STATUS_COMPLETED
        record.completed_at = completed_at
        record.encrypted_card_data = encrypted
        self.db.commit()
        self.db.refresh(record)

        return {
            "message": "Credit card authorization recorded successfully.",
            "status": record.status,
            "completed_at": completed_at,
            "authorization_id": record.id,
        }

    def purge_card_data(self, authorization_id: str) -> dict:
        record = self.db.get(CreditCardAuthorization, authorization_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Authorization record not found.")
        if record.status != CC_AUTH_STATUS_COMPLETED:
            raise HTTPException(status_code=400, detail="Only completed authorizations can be purged.")
        if not record.encrypted_card_data:
            raise HTTPException(status_code=400, detail="Card data has already been purged.")

        record.encrypted_card_data = None
        self.db.commit()
        self.db.refresh(record)

        return {
            "message": "Card data securely purged. Authorization audit record retained.",
            "authorization_id": record.id,
            "status": record.status,
            "card_data_purged": True,
        }
