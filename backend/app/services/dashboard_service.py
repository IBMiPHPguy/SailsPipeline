from sqlalchemy.orm import Session

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED, REQUEST_STATUS_OPEN
from app.models import TravelRequest
from app.schemas import DashboardResponse
from app.services.request_service import build_dashboard_open_request, dashboard_query


def get_dashboard(db: Session) -> DashboardResponse:
    open_requests = (
        dashboard_query(db)
        .filter(TravelRequest.status == REQUEST_STATUS_OPEN)
        .all()
    )

    dashboard_items = [build_dashboard_open_request(request) for request in open_requests]
    dashboard_items.sort(key=lambda item: item.last_worked_at)
    stale_count = sum(1 for item in dashboard_items if item.is_stale)
    closed_requests = db.query(TravelRequest).filter(TravelRequest.status == REQUEST_STATUS_CLOSED)
    closed_count = closed_requests.count()
    purchased_closed_count = closed_requests.filter(
        TravelRequest.close_reason == PRIMARY_CLOSE_REASON
    ).count()
    other_closed_count = closed_count - purchased_closed_count
    successful_sales_close_rate = (
        round((purchased_closed_count / closed_count) * 100, 1) if closed_count else None
    )

    return DashboardResponse(
        open_count=len(dashboard_items),
        stale_count=stale_count,
        closed_count=closed_count,
        purchased_closed_count=purchased_closed_count,
        other_closed_count=other_closed_count,
        successful_sales_close_rate=successful_sales_close_rate,
        open_requests=dashboard_items,
    )
