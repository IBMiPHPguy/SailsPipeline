from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cc_auth_vault import decrypt_card_payload, verify_vault_access_key
from app.constants import CC_AUTH_STATUS_COMPLETED
from app.models import CreditCardAuthorization
from app.services.agency_service import assert_child_belongs_to_request, get_travel_request_for_agency, require_record_for_agency
from app.services.cc_auth_service import CCAuthService
from app.tenant_context import require_current_agency_id


def _load_authorization_for_request(
    db: Session,
    *,
    request_id: int,
    authorization_id: str,
) -> CreditCardAuthorization:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    record = db.get(CreditCardAuthorization, authorization_id)
    require_record_for_agency(record, agency_id=agency_id)
    assert_child_belongs_to_request(
        child_agency_id=record.agency_id,
        child_travel_request_id=record.travel_request_id,
        request_id=request_id,
        agency_id=agency_id,
    )
    return record


def list_request_cc_authorizations(db: Session, *, request_id: int) -> list[dict]:
    agency_id = require_current_agency_id()
    get_travel_request_for_agency(db, request_id, agency_id)
    records = (
        db.query(CreditCardAuthorization)
        .filter(
            CreditCardAuthorization.travel_request_id == request_id,
            CreditCardAuthorization.agency_id == agency_id,
        )
        .order_by(CreditCardAuthorization.created_at.desc())
        .all()
    )
    return [
        {
            "id": record.id,
            "status": record.status,
            "created_at": record.created_at,
            "completed_at": record.completed_at,
            "expires_at": record.expires_at,
            "has_card_data": bool(record.encrypted_card_data),
            "card_data_purged": record.status == CC_AUTH_STATUS_COMPLETED and not record.encrypted_card_data,
        }
        for record in records
    ]


def reveal_request_cc_authorization(
    db: Session,
    *,
    request_id: int,
    authorization_id: str,
    vault_access_key: str,
) -> dict:
    verify_vault_access_key(vault_access_key)
    record = _load_authorization_for_request(db, request_id=request_id, authorization_id=authorization_id)
    if record.status != CC_AUTH_STATUS_COMPLETED:
        raise HTTPException(status_code=400, detail="Card data is only available for completed authorizations.")
    if not record.encrypted_card_data:
        raise HTTPException(status_code=410, detail="Card data has been purged from the vault.")

    card = decrypt_card_payload(record.encrypted_card_data)
    return {
        "authorization_id": record.id,
        "card": card,
    }


def purge_request_cc_authorization(db: Session, *, request_id: int, authorization_id: str) -> dict:
    record = _load_authorization_for_request(db, request_id=request_id, authorization_id=authorization_id)
    agency_id = require_current_agency_id()
    service = CCAuthService(db)
    return service.purge_card_data(authorization_id=record.id, agency_id=agency_id)
