from sqlalchemy.orm import Session

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED, REQUEST_STATUS_OPEN
from app.models import TravelRequest, User
from app.schemas import DashboardResponse
from app.services.agency_rollup_service import get_or_refresh_dashboard_rollup
from app.services.agent_capability_service import get_capabilities_for_user
from app.services.booked_cruise_metrics import calculate_open_pipeline_value
from app.services.request_service import (
    build_dashboard_open_request,
    count_stale_open_requests,
    dashboard_query,
)


def _dashboard_for_owned_requests(
    db: Session,
    agency_id: str,
    owned_by_user_id: int,
) -> DashboardResponse:
    open_requests = (
        dashboard_query(db)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequest.status == REQUEST_STATUS_OPEN,
            TravelRequest.created_by_id == owned_by_user_id,
        )
        .all()
    )
    open_count = len(open_requests)
    stale_count = sum(1 for request in open_requests if build_dashboard_open_request(request).is_stale)

    closed_query = db.query(TravelRequest).filter(
        TravelRequest.agency_id == agency_id,
        TravelRequest.status == REQUEST_STATUS_CLOSED,
        TravelRequest.created_by_id == owned_by_user_id,
    )
    closed_count = closed_query.count()
    purchased_closed_count = closed_query.filter(
        TravelRequest.close_reason == PRIMARY_CLOSE_REASON
    ).count()
    other_closed_count = closed_count - purchased_closed_count
    successful_sales_close_rate = (
        round((purchased_closed_count / closed_count) * 100, 1) if closed_count else None
    )

    return DashboardResponse(
        open_count=open_count,
        stale_count=stale_count,
        closed_count=closed_count,
        purchased_closed_count=purchased_closed_count,
        other_closed_count=other_closed_count,
        successful_sales_close_rate=successful_sales_close_rate,
        total_pipeline_value=calculate_open_pipeline_value(
            db,
            agency_id=agency_id,
            owned_by_user_id=owned_by_user_id,
        ),
    )


def get_dashboard(db: Session, agency_id: str, current_user: User | None = None) -> DashboardResponse:
    if current_user is not None:
        caps = get_capabilities_for_user(db, current_user)
        if not caps.is_unrestricted and not caps.view_other_agent_requests:
            return _dashboard_for_owned_requests(db, agency_id, current_user.id)

    rollup = get_or_refresh_dashboard_rollup(db, agency_id)

    closed_count = rollup.closed_count
    purchased_closed_count = rollup.purchased_closed_count
    other_closed_count = closed_count - purchased_closed_count
    successful_sales_close_rate = (
        round((purchased_closed_count / closed_count) * 100, 1) if closed_count else None
    )

    return DashboardResponse(
        open_count=rollup.open_leads_count,
        stale_count=count_stale_open_requests(db, agency_id),
        closed_count=closed_count,
        purchased_closed_count=purchased_closed_count,
        other_closed_count=other_closed_count,
        successful_sales_close_rate=successful_sales_close_rate,
        total_pipeline_value=float(rollup.total_pipeline_value or 0),
    )
