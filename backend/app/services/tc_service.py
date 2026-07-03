from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.constants import (
    TC_REQUEST_STATUS_COMPLETED,
    TC_REQUEST_STATUS_EXPIRED,
    TC_REQUEST_STATUS_PENDING,
    TC_STATUS_ACCEPTED,
    TC_TTL_HOURS,
)
from app.models import Agency, ClientTermsAgreement, ClientTermsRequest, TravelRequest
from app.services.agency_settings_service import resolve_terms_text
from app.services.passenger_service import get_primary_passenger
from app.services.tc_workflow_service import complete_open_master_terms_tasks, sync_master_terms_tasks_for_request
from app.tc_helpers import master_terms_version_hash, render_master_terms_for_agency


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TCService:
    """Sign-once Master Terms & Conditions lifecycle for agency clients."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _resolve_client_id(self, travel_request_id: int) -> tuple[TravelRequest, int]:
        request = self.db.get(TravelRequest, travel_request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Travel request not found.")

        primary = get_primary_passenger(self.db, travel_request_id)
        if primary is None:
            raise HTTPException(
                status_code=400,
                detail="A linked client record is required before sending Master Terms & Conditions.",
            )
        return request, primary.passenger_id

    def _build_portal_url(self, token: str) -> str:
        base = settings.terms_portal_base_url.rstrip("/") + "/"
        return urljoin(base, token)

    def _expire_pending_tokens(self, travel_request_id: int) -> None:
        pending = (
            self.db.query(ClientTermsRequest)
            .filter(
                ClientTermsRequest.travel_request_id == travel_request_id,
                ClientTermsRequest.status == TC_REQUEST_STATUS_PENDING,
            )
            .all()
        )
        for record in pending:
            record.status = TC_REQUEST_STATUS_EXPIRED
        if pending:
            self.db.flush()

    async def check_global_status(self, client_id: int, agency_id: str) -> dict:
        agreement = (
            self.db.query(ClientTermsAgreement)
            .filter(
                ClientTermsAgreement.client_id == client_id,
                ClientTermsAgreement.agency_id == agency_id,
                ClientTermsAgreement.status == TC_STATUS_ACCEPTED,
            )
            .order_by(ClientTermsAgreement.accepted_at.desc())
            .first()
        )
        if agreement is None:
            return {
                "on_file": False,
                "client_id": client_id,
                "agency_id": agency_id,
            }

        return {
            "on_file": True,
            "client_id": client_id,
            "agency_id": agency_id,
            "accepted_at": agreement.accepted_at.isoformat(),
            "version_hash": agreement.version_hash,
            "travel_request_id": agreement.travel_request_id,
            "ip_address": agreement.ip_address,
        }

    async def check_request_status(self, travel_request_id: int) -> dict:
        request, client_id = self._resolve_client_id(travel_request_id)
        status = await self.check_global_status(client_id, request.agency_id)
        status["travel_request_id"] = travel_request_id
        status["task_auto_completed"] = False

        if status.get("on_file"):
            completed_count = sync_master_terms_tasks_for_request(
                self.db,
                travel_request_id=travel_request_id,
            )
            if completed_count:
                self.db.commit()
                status["task_auto_completed"] = True

        return status

    def resolve_client_id_for_request(self, travel_request_id: int) -> tuple[TravelRequest, int]:
        return self._resolve_client_id(travel_request_id)

    async def create_tc_request(self, travel_request_id: int) -> str:
        request, client_id = self._resolve_client_id(travel_request_id)

        existing = await self.check_global_status(client_id, request.agency_id)
        if existing.get("on_file"):
            raise HTTPException(
                status_code=409,
                detail="Master Terms & Conditions are already on file for this client.",
            )

        self._expire_pending_tokens(travel_request_id)

        token = secrets.token_urlsafe(48)
        expires_at = _utcnow() + timedelta(hours=TC_TTL_HOURS)
        record = ClientTermsRequest(
            id=str(uuid.uuid4()),
            agency_id=request.agency_id,
            client_id=client_id,
            travel_request_id=travel_request_id,
            secure_token=token,
            status=TC_REQUEST_STATUS_PENDING,
            expires_at=expires_at,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return self._build_portal_url(token)

    def _get_record_by_token(self, token: str) -> ClientTermsRequest | None:
        normalized = token.strip()
        if not normalized:
            return None
        return (
            self.db.query(ClientTermsRequest)
            .filter(ClientTermsRequest.secure_token == normalized)
            .first()
        )

    async def validate_token(self, token: str) -> dict:
        normalized = token.strip()
        if not normalized:
            return {"valid": False, "reason": "missing_token"}

        record = self._get_record_by_token(normalized)
        if record is None:
            return {"valid": False, "reason": "not_found"}

        now = _utcnow()
        if record.status != TC_REQUEST_STATUS_PENDING:
            return {
                "valid": False,
                "reason": "invalid_status",
                "status": record.status,
                "travel_request_id": record.travel_request_id,
            }

        if record.expires_at <= now:
            record.status = TC_REQUEST_STATUS_EXPIRED
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
            "client_id": record.client_id,
            "request_id": record.id,
            "expires_at": record.expires_at.isoformat(),
            "status": record.status,
        }

    async def record_acceptance(self, token: str, ip_address: str) -> bool:
        validation = await self.validate_token(token)
        if not validation.get("valid"):
            reason = validation.get("reason", "invalid_token")
            detail = {
                "missing_token": "Terms acceptance token is required.",
                "not_found": "Terms acceptance link was not found.",
                "expired": "This terms acceptance link has expired.",
                "invalid_status": "This terms acceptance link is no longer active.",
            }.get(reason, "Terms acceptance link is not valid.")
            raise HTTPException(status_code=410, detail=detail)

        record = self._get_record_by_token(token)
        if record is None:
            raise HTTPException(status_code=404, detail="Terms acceptance link was not found.")

        request = self.db.get(TravelRequest, record.travel_request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Travel request not found.")

        from app.models import Agency

        agency = self.db.get(Agency, record.agency_id)
        version_hash = master_terms_version_hash(agency=agency)
        accepted_at = _utcnow()
        normalized_ip = (ip_address or "").strip()[:64] or None

        agreement = (
            self.db.query(ClientTermsAgreement)
            .filter(
                ClientTermsAgreement.agency_id == record.agency_id,
                ClientTermsAgreement.client_id == record.client_id,
            )
            .first()
        )
        if agreement is None:
            agreement = ClientTermsAgreement(
                agency_id=record.agency_id,
                client_id=record.client_id,
                travel_request_id=record.travel_request_id,
                status=TC_STATUS_ACCEPTED,
                accepted_at=accepted_at,
                ip_address=normalized_ip,
                version_hash=version_hash,
            )
            self.db.add(agreement)
        else:
            agreement.status = TC_STATUS_ACCEPTED
            agreement.accepted_at = accepted_at
            agreement.ip_address = normalized_ip
            agreement.version_hash = version_hash
            agreement.travel_request_id = record.travel_request_id

        record.status = TC_REQUEST_STATUS_COMPLETED
        record.completed_at = accepted_at
        complete_open_master_terms_tasks(
            self.db,
            travel_request_id=record.travel_request_id,
            accepted_at=accepted_at,
            source="master_terms_portal",
        )
        self.db.commit()
        return True

    def render_terms_for_agency(self, *, agency: Agency | None) -> str:
        if agency is None:
            return render_master_terms_for_agency(None)
        return resolve_terms_text(self.db, agency_id=agency.id, agency=agency)
