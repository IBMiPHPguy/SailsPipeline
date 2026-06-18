from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.constants import QUOTED_INSURANCE_STATUS_DECLINED, QUOTED_INSURANCE_STATUS_PROPOSED
from app.models import QuotedInsurance, User
from app.schemas import QuotedInsuranceCreate, QuotedInsuranceUpdate
from app.services.request_service import get_open_request, touch_request


def load_quoted_insurance(db: Session, quote_id: int) -> QuotedInsurance:
    return (
        db.query(QuotedInsurance)
        .options(
            joinedload(QuotedInsurance.created_by),
            joinedload(QuotedInsurance.updated_by),
        )
        .filter(QuotedInsurance.id == quote_id)
        .one()
    )


def add_quoted_insurance(
    db: Session,
    *,
    request_id: int,
    payload: QuotedInsuranceCreate,
    current_user: User,
) -> QuotedInsurance:
    request = get_open_request(db, request_id)
    quote = QuotedInsurance(
        travel_request_id=request_id,
        **payload.model_dump(),
        status=QUOTED_INSURANCE_STATUS_PROPOSED,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    touch_request(request, current_user)
    db.add(quote)
    db.commit()
    return load_quoted_insurance(db, quote.id)


def update_quoted_insurance(
    db: Session,
    *,
    request_id: int,
    quote_id: int,
    payload: QuotedInsuranceUpdate,
    current_user: User,
) -> QuotedInsurance:
    request = get_open_request(db, request_id)
    quote = db.get(QuotedInsurance, quote_id)
    if quote is None or quote.travel_request_id != request_id:
        raise HTTPException(status_code=404, detail="Quoted insurance not found.")

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates:
        new_status = updates["status"]
        if new_status == QUOTED_INSURANCE_STATUS_DECLINED and quote.status != QUOTED_INSURANCE_STATUS_DECLINED:
            quote.declined_at = datetime.now(UTC).replace(tzinfo=None)
        elif new_status != QUOTED_INSURANCE_STATUS_DECLINED:
            quote.declined_at = None

    for field, value in updates.items():
        setattr(quote, field, value)

    quote.updated_by_id = current_user.id
    touch_request(request, current_user)
    db.commit()
    return load_quoted_insurance(db, quote.id)
