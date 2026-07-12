from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urljoin

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import (
    INSURANCE_STATUS_ANNUAL_CONFIRMED,
    INSURANCE_STATUS_PENDING,
    INSURANCE_STATUS_WAIVER_SIGNED,
    INSURANCE_WAIVER_REQUEST_STATUS_COMPLETED,
    INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED,
    INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
    INSURANCE_WAIVER_TTL_HOURS,
    QUOTED_INSURANCE_STATUS_ACCEPTED,
    QUOTED_INSURANCE_STATUS_DECLINED,
    QUOTED_INSURANCE_STATUS_PROPOSED,
)
from app.models import InsuranceWaiverRequest, QuotedInsurance, RequestInsuranceTracking, TravelRequest, User
from app.schemas import AnnualInsuranceUpdate
from app.services.passenger_service import get_primary_passenger
from app.services.request_service import get_open_request, touch_request


def _annual_expiration_is_valid(expires_at: date | None) -> bool:
    return expires_at is not None and expires_at > date.today()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class InsuranceService:
    """Per-request insurance verification and waiver lifecycle."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _build_portal_url(self, token: str) -> str:
        base = settings.insurance_portal_base_url.rstrip("/") + "/"
        return urljoin(base, token)

    def ensure_tracking(self, request: TravelRequest) -> RequestInsuranceTracking:
        tracking = (
            self.db.query(RequestInsuranceTracking)
            .filter(RequestInsuranceTracking.travel_request_id == request.id)
            .first()
        )
        if tracking is not None:
            return tracking

        tracking = RequestInsuranceTracking(
            agency_id=request.agency_id,
            travel_request_id=request.id,
            insurance_status=INSURANCE_STATUS_PENDING,
        )
        self.db.add(tracking)
        self.db.flush()
        return tracking

    def _expire_pending_waiver_tokens(self, travel_request_id: int) -> None:
        pending = (
            self.db.query(InsuranceWaiverRequest)
            .filter(
                InsuranceWaiverRequest.travel_request_id == travel_request_id,
                InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
            )
            .all()
        )
        for record in pending:
            record.status = INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED
        if pending:
            self.db.flush()

    async def create_waiver_request(self, travel_request_id: int) -> tuple[str, bool]:
        request = get_open_request(self.db, travel_request_id)
        if not request.email.strip():
            raise HTTPException(status_code=400, detail="Travel request is missing a client email address.")

        self.ensure_tracking(request)
        self._expire_stale_pending_waivers(travel_request_id)
        now = _utcnow()
        active_pending = (
            self.db.query(InsuranceWaiverRequest)
            .filter(
                InsuranceWaiverRequest.travel_request_id == travel_request_id,
                InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
                InsuranceWaiverRequest.expires_at > now,
            )
            .count()
        )
        had_active_pending = active_pending > 0
        self._expire_pending_waiver_tokens(travel_request_id)

        token = secrets.token_urlsafe(48)
        expires_at = now + timedelta(hours=INSURANCE_WAIVER_TTL_HOURS)
        record = InsuranceWaiverRequest(
            id=str(uuid.uuid4()),
            agency_id=request.agency_id,
            travel_request_id=travel_request_id,
            secure_token=token,
            status=INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return self._build_portal_url(token), had_active_pending

    def _get_waiver_by_token(self, token: str) -> InsuranceWaiverRequest | None:
        normalized = token.strip()
        if not normalized:
            return None
        return (
            self.db.query(InsuranceWaiverRequest)
            .filter(InsuranceWaiverRequest.secure_token == normalized)
            .first()
        )

    async def validate_token(self, token: str) -> dict:
        normalized = token.strip()
        if not normalized:
            return {"valid": False, "reason": "missing_token"}

        record = self._get_waiver_by_token(normalized)
        if record is None:
            return {"valid": False, "reason": "not_found"}

        now = _utcnow()
        if record.status != INSURANCE_WAIVER_REQUEST_STATUS_PENDING:
            return {
                "valid": False,
                "reason": "invalid_status",
                "travel_request_id": record.travel_request_id,
            }

        if record.expires_at <= now:
            record.status = INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED
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
            "expires_at": record.expires_at.isoformat(),
            "status": record.status,
        }

    async def record_waiver_signature(self, token: str, ip_address: str) -> bool:
        validation = await self.validate_token(token)
        if not validation.get("valid"):
            reason = validation.get("reason", "invalid_token")
            detail = {
                "missing_token": "Insurance waiver token is required.",
                "not_found": "Insurance waiver link was not found.",
                "expired": "This insurance waiver link has expired.",
                "invalid_status": "This insurance waiver link is no longer active.",
            }.get(reason, "Insurance waiver link is not valid.")
            raise HTTPException(status_code=410 if reason != "not_found" else 404, detail=detail)

        record = self._get_waiver_by_token(token.strip())
        if record is None:
            raise HTTPException(status_code=404, detail="Insurance waiver link was not found.")

        now = _utcnow()
        record.status = INSURANCE_WAIVER_REQUEST_STATUS_COMPLETED
        record.completed_at = now

        request = self.db.get(TravelRequest, record.travel_request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Travel request not found.")

        tracking = self.ensure_tracking(request)
        tracking.insurance_status = INSURANCE_STATUS_WAIVER_SIGNED
        tracking.waiver_signed_at = now
        tracking.waiver_ip = (ip_address or "").strip()[:64] or None

        self.db.commit()
        return True

    def _quote_summary(self, travel_request_id: int) -> dict[str, bool]:
        quotes = (
            self.db.query(QuotedInsurance)
            .filter(QuotedInsurance.travel_request_id == travel_request_id)
            .all()
        )
        if not quotes:
            return {
                "has_proposed_quotes": False,
                "has_accepted_quote": False,
                "all_quotes_declined": False,
            }

        active = [quote for quote in quotes if quote.status != QUOTED_INSURANCE_STATUS_DECLINED]
        return {
            "has_proposed_quotes": any(quote.status == QUOTED_INSURANCE_STATUS_PROPOSED for quote in quotes),
            "has_accepted_quote": any(quote.status == QUOTED_INSURANCE_STATUS_ACCEPTED for quote in quotes),
            "all_quotes_declined": len(active) == 0,
        }

    def _completion_state(
        self,
        *,
        has_annual_insurance: bool,
        annual_expires_at,
        policy_number: str | None,
        insurance_status: str,
        quote_summary: dict[str, bool],
    ) -> tuple[bool, str | None]:
        if has_annual_insurance:
            if not policy_number or not annual_expires_at:
                return False, "Enter the annual policy number and expiration date before completing this task."
            if not _annual_expiration_is_valid(annual_expires_at):
                return (
                    False,
                    "Annual insurance has expired. Update the policy details or clear annual coverage to use per-trip insurance.",
                )
            return True, None

        if quote_summary["has_accepted_quote"]:
            return True, None

        if quote_summary["all_quotes_declined"] or insurance_status == INSURANCE_STATUS_WAIVER_SIGNED:
            if insurance_status != INSURANCE_STATUS_WAIVER_SIGNED:
                return False, "A signed insurance waiver is required before this task can be completed."
            return True, None

        if not quote_summary["has_proposed_quotes"]:
            return False, "Add insurance quotes or send the waiver email if the client declines coverage."

        return False, "Resolve insurance quotes (acceptance or signed waiver) before completing this task."

    def _expire_stale_pending_waivers(self, travel_request_id: int) -> None:
        now = _utcnow()
        pending = (
            self.db.query(InsuranceWaiverRequest)
            .filter(
                InsuranceWaiverRequest.travel_request_id == travel_request_id,
                InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
                InsuranceWaiverRequest.expires_at <= now,
            )
            .all()
        )
        for record in pending:
            record.status = INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED
        if pending:
            self.db.flush()

    def _waiver_request_summary(self, travel_request_id: int, *, waiver_signed: bool) -> dict:
        self._expire_stale_pending_waivers(travel_request_id)

        if waiver_signed:
            latest_completed = (
                self.db.query(InsuranceWaiverRequest)
                .filter(
                    InsuranceWaiverRequest.travel_request_id == travel_request_id,
                    InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_COMPLETED,
                )
                .order_by(InsuranceWaiverRequest.completed_at.desc())
                .first()
            )
            return {
                "waiver_request_status": "completed",
                "waiver_sent_at": latest_completed.created_at.isoformat() if latest_completed else None,
                "waiver_expires_at": None,
            }

        pending = (
            self.db.query(InsuranceWaiverRequest)
            .filter(
                InsuranceWaiverRequest.travel_request_id == travel_request_id,
                InsuranceWaiverRequest.status == INSURANCE_WAIVER_REQUEST_STATUS_PENDING,
            )
            .order_by(InsuranceWaiverRequest.created_at.desc())
            .first()
        )
        if pending is not None and pending.expires_at > _utcnow():
            return {
                "waiver_request_status": "pending",
                "waiver_sent_at": pending.created_at.isoformat(),
                "waiver_expires_at": pending.expires_at.isoformat(),
            }

        latest = (
            self.db.query(InsuranceWaiverRequest)
            .filter(InsuranceWaiverRequest.travel_request_id == travel_request_id)
            .order_by(InsuranceWaiverRequest.created_at.desc())
            .first()
        )
        if latest is not None and latest.status == INSURANCE_WAIVER_REQUEST_STATUS_EXPIRED:
            return {
                "waiver_request_status": "expired",
                "waiver_sent_at": latest.created_at.isoformat(),
                "waiver_expires_at": latest.expires_at.isoformat(),
            }

        return {
            "waiver_request_status": "none",
            "waiver_sent_at": None,
            "waiver_expires_at": None,
        }

    async def get_request_status(self, travel_request_id: int) -> dict:
        request = get_open_request(self.db, travel_request_id)
        tracking = self.ensure_tracking(request)
        self.db.commit()

        primary = get_primary_passenger(self.db, travel_request_id)
        has_annual = bool(primary and primary.has_annual_insurance)
        quote_summary = self._quote_summary(travel_request_id)

        annual_expires_at = primary.annual_insurance_expires_at if primary else None
        annual_policy_number = primary.annual_insurance_policy_number if primary else None
        annual_is_valid = (
            has_annual
            and bool(annual_policy_number)
            and _annual_expiration_is_valid(annual_expires_at)
        )
        annual_is_expired = (
            has_annual
            and annual_expires_at is not None
            and not _annual_expiration_is_valid(annual_expires_at)
        )

        can_complete, blocked_reason = self._completion_state(
            has_annual_insurance=has_annual,
            annual_expires_at=annual_expires_at,
            policy_number=annual_policy_number,
            insurance_status=tracking.insurance_status,
            quote_summary=quote_summary,
        )

        waiver_signed = tracking.insurance_status == INSURANCE_STATUS_WAIVER_SIGNED
        waiver_request = self._waiver_request_summary(travel_request_id, waiver_signed=waiver_signed)
        self.db.commit()
        client_name = (
            f"{primary.first_name} {primary.last_name}".strip()
            if primary
            else f"{request.first_name} {request.last_name}".strip()
        )

        return {
            "travel_request_id": travel_request_id,
            "insurance_status": tracking.insurance_status,
            "waiver_signed": waiver_signed,
            "waiver_signed_at": tracking.waiver_signed_at.isoformat() if tracking.waiver_signed_at else None,
            "waiver_request_status": waiver_request["waiver_request_status"],
            "waiver_sent_at": waiver_request["waiver_sent_at"],
            "waiver_expires_at": waiver_request["waiver_expires_at"],
            "has_annual_insurance": has_annual,
            "annual_insurance_expires_at": annual_expires_at,
            "annual_insurance_policy_number": annual_policy_number,
            "annual_insurance_is_valid": annual_is_valid,
            "annual_insurance_is_expired": annual_is_expired,
            "primary_passenger_id": primary.id if primary else None,
            "client_name": client_name,
            "client_registry_passenger_id": primary.passenger_id if primary else None,
            "has_accepted_quote": quote_summary["has_accepted_quote"],
            "all_quotes_declined": quote_summary["all_quotes_declined"],
            "has_proposed_quotes": quote_summary["has_proposed_quotes"],
            "can_complete_task": can_complete,
            "completion_blocked_reason": blocked_reason,
        }

    def update_annual_insurance(
        self,
        *,
        travel_request_id: int,
        payload: AnnualInsuranceUpdate,
        current_user: User,
    ) -> dict:
        request = get_open_request(self.db, travel_request_id, current_user)
        primary = get_primary_passenger(self.db, travel_request_id)
        if primary is None:
            raise HTTPException(status_code=400, detail="A primary passenger is required.")
        if not primary.has_annual_insurance:
            raise HTTPException(
                status_code=400,
                detail="Annual travel insurance is not enabled on this client's profile.",
            )

        updates = payload.model_dump(exclude_unset=True)
        updates.pop("has_annual_insurance", None)
        for field, value in updates.items():
            setattr(primary, field, value)

        if not primary.annual_insurance_policy_number or not primary.annual_insurance_expires_at:
            raise HTTPException(
                status_code=400,
                detail="Annual policy number and expiration date are required.",
            )
        if not _annual_expiration_is_valid(primary.annual_insurance_expires_at):
            raise HTTPException(
                status_code=400,
                detail=(
                    "The expiration date must be in the future. Enter a valid policy expiration "
                    "or remove annual insurance to use per-trip coverage."
                ),
            )

        tracking = self.ensure_tracking(request)
        if (
            primary.has_annual_insurance
            and primary.annual_insurance_policy_number
            and _annual_expiration_is_valid(primary.annual_insurance_expires_at)
        ):
            tracking.insurance_status = INSURANCE_STATUS_ANNUAL_CONFIRMED
        elif primary.has_annual_insurance:
            tracking.insurance_status = INSURANCE_STATUS_PENDING

        touch_request(request, current_user)
        self.db.commit()
        return {"updated": True}

    def clear_annual_insurance(
        self,
        *,
        travel_request_id: int,
        current_user: User,
    ) -> None:
        request = get_open_request(self.db, travel_request_id, current_user)
        primary = get_primary_passenger(self.db, travel_request_id)
        if primary is None:
            raise HTTPException(status_code=400, detail="A primary passenger is required.")
        if not primary.has_annual_insurance:
            raise HTTPException(
                status_code=400,
                detail="Annual travel insurance is not enabled on this client's profile.",
            )

        primary.has_annual_insurance = False
        primary.annual_insurance_expires_at = None
        primary.annual_insurance_policy_number = None

        tracking = self.ensure_tracking(request)
        tracking.insurance_status = INSURANCE_STATUS_PENDING

        touch_request(request, current_user)
        self.db.commit()

    def confirm_annual_insurance(
        self,
        *,
        travel_request_id: int,
        current_user: User,
    ) -> None:
        request = get_open_request(self.db, travel_request_id, current_user)
        primary = get_primary_passenger(self.db, travel_request_id)
        if primary is None or not primary.has_annual_insurance:
            raise HTTPException(status_code=400, detail="Annual insurance is not enabled for the primary passenger.")
        if not primary.annual_insurance_policy_number or not primary.annual_insurance_expires_at:
            raise HTTPException(
                status_code=400,
                detail="Annual policy number and expiration date are required.",
            )

        tracking = self.ensure_tracking(request)
        tracking.insurance_status = INSURANCE_STATUS_ANNUAL_CONFIRMED
        touch_request(request, current_user)
        self.db.commit()

    async def send_insurance_waiver_email(self, travel_request_id: int, current_user: User) -> dict[str, object]:
        from app.services.insurance_communication_service import send_insurance_waiver_email

        request = get_open_request(self.db, travel_request_id, current_user)
        return await send_insurance_waiver_email(self.db, request=request, current_user=current_user)
