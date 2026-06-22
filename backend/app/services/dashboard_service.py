from sqlalchemy.orm import Session

from app.schemas import DashboardResponse
from app.services.agency_rollup_service import get_or_refresh_dashboard_rollup


def get_dashboard(db: Session, agency_id: str) -> DashboardResponse:
    rollup = get_or_refresh_dashboard_rollup(db, agency_id)

    closed_count = rollup.closed_count
    purchased_closed_count = rollup.purchased_closed_count
    other_closed_count = closed_count - purchased_closed_count
    successful_sales_close_rate = (
        round((purchased_closed_count / closed_count) * 100, 1) if closed_count else None
    )

    return DashboardResponse(
        open_count=rollup.open_leads_count,
        stale_count=rollup.stale_count,
        closed_count=closed_count,
        purchased_closed_count=purchased_closed_count,
        other_closed_count=other_closed_count,
        successful_sales_close_rate=successful_sales_close_rate,
        total_pipeline_value=float(rollup.total_pipeline_value or 0),
    )
