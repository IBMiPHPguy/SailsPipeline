from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.constants import QUOTED_INSURANCE_STATUS_DECLINED, QUOTED_INSURANCE_STATUS_PROPOSED
from app.models import QuotedInsurance, User
from app.schemas import QuotedInsuranceCreate, QuotedInsuranceUpdate
from app.services.agency_service import assert_child_belongs_to_request, require_record_for_agency
from app.services.request_service import get_open_request, touch_request
from app.tenant_context import require_current_agency_id


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
        agency_id=request.agency_id,
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
    require_record_for_agency(quote, agency_id=require_current_agency_id())
    assert_child_belongs_to_request(
        child_agency_id=quote.agency_id,
        child_travel_request_id=quote.travel_request_id,
        request_id=request_id,
        agency_id=request.agency_id,
    )

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
