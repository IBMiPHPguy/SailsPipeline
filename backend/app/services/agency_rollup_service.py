from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import (
    PRIMARY_CLOSE_REASON,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
)
from app.models import Agency, AgencyDashboardRollup, AgencyReportMetadataCache, Passenger, ProposedCruise, TravelRequest, User
from app.services.booked_cruise_metrics import (
    calculate_open_pipeline_value,
    get_booked_cruise_aggregates,
)
from app.services.request_service import build_dashboard_open_request, dashboard_query

logger = logging.getLogger(__name__)

_refresh_lock = threading.Lock()
_pending_agency_ids: set[str] = set()


def schedule_agency_rollup_refresh(agency_id: str | None) -> None:
    """Queue an asynchronous rollup refresh for one agency."""
    if not agency_id:
        return
    with _refresh_lock:
        _pending_agency_ids.add(agency_id)


def drain_pending_agency_rollup_refreshes() -> list[str]:
    with _refresh_lock:
        agency_ids = sorted(_pending_agency_ids)
        _pending_agency_ids.clear()
    return agency_ids


def refresh_agency_dashboard_rollups(db: Session, agency_id: str) -> AgencyDashboardRollup:
    open_requests = (
        dashboard_query(db)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequest.status == REQUEST_STATUS_OPEN,
        )
        .all()
    )
    dashboard_items = [build_dashboard_open_request(request) for request in open_requests]
    stale_count = sum(1 for item in dashboard_items if item.is_stale)
    open_leads_count = len(dashboard_items)

    closed_query = db.query(TravelRequest).filter(
        TravelRequest.agency_id == agency_id,
        TravelRequest.status == REQUEST_STATUS_CLOSED,
    )
    closed_count = closed_query.count()
    purchased_closed_count = closed_query.filter(
        TravelRequest.close_reason == PRIMARY_CLOSE_REASON
    ).count()

    proposals_pending_count = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_PROPOSED,
        )
        .count()
    )

    booked_aggregates = get_booked_cruise_aggregates(db, agency_id)
    total_pipeline_value = calculate_open_pipeline_value(db, agency_id=agency_id)
    refreshed_at = datetime.now(UTC).replace(tzinfo=None)

    rollup = db.get(AgencyDashboardRollup, agency_id)
    if rollup is None:
        rollup = AgencyDashboardRollup(agency_id=agency_id)
        db.add(rollup)

    rollup.open_leads_count = open_leads_count
    rollup.proposals_pending_count = proposals_pending_count
    rollup.completed_bookings_count = booked_aggregates.booking_count
    rollup.total_volume_booked = booked_aggregates.total_volume
    rollup.total_commission_booked = booked_aggregates.total_commission
    rollup.stale_count = stale_count
    rollup.closed_count = closed_count
    rollup.purchased_closed_count = purchased_closed_count
    rollup.total_pipeline_value = total_pipeline_value
    rollup.last_refreshed_at = refreshed_at
    db.commit()
    db.refresh(rollup)
    return rollup


def refresh_agency_report_metadata_cache(db: Session, agency_id: str) -> AgencyReportMetadataCache:
    updated_advisors = {
        username
        for (username,) in db.query(User.username)
        .join(TravelRequest, TravelRequest.updated_by_id == User.id)
        .filter(
            TravelRequest.agency_id == agency_id,
            User.agency_id == agency_id,
            User.is_active.is_(True),
        )
        .all()
        if username
    }
    created_advisors = {
        username
        for (username,) in db.query(User.username)
        .join(TravelRequest, TravelRequest.created_by_id == User.id)
        .filter(
            TravelRequest.agency_id == agency_id,
            User.agency_id == agency_id,
            User.is_active.is_(True),
        )
        .all()
        if username
    }
    active_advisor_names = sorted(updated_advisors | created_advisors)
    active_residence_states = sorted(
        {
            state.strip()
            for (state,) in (
                db.query(Passenger.state_or_province)
                .filter(
                    Passenger.agency_id == agency_id,
                    Passenger.is_active.is_(True),
                    Passenger.state_or_province.isnot(None),
                    func.trim(Passenger.state_or_province) != "",
                )
                .distinct()
                .all()
            )
            if state and state.strip()
        }
    )
    refreshed_at = datetime.now(UTC).replace(tzinfo=None)

    cache = db.get(AgencyReportMetadataCache, agency_id)
    if cache is None:
        cache = AgencyReportMetadataCache(agency_id=agency_id)
        db.add(cache)

    cache.active_advisor_names = active_advisor_names
    cache.active_residence_states = active_residence_states
    cache.last_refreshed_at = refreshed_at
    db.commit()
    db.refresh(cache)
    return cache


def refresh_agency_rollups(db: Session, agency_id: str) -> tuple[AgencyDashboardRollup, AgencyReportMetadataCache]:
    dashboard = refresh_agency_dashboard_rollups(db, agency_id)
    metadata = refresh_agency_report_metadata_cache(db, agency_id)
    return dashboard, metadata


def refresh_all_agency_rollups(db: Session) -> int:
    agency_ids = [row[0] for row in db.query(Agency.id).all()]
    for agency_id in agency_ids:
        try:
            refresh_agency_rollups(db, agency_id)
        except Exception:
            logger.exception("Failed to refresh rollups for agency %s", agency_id)
            db.rollback()
    return len(agency_ids)


def process_scheduled_agency_rollup_refreshes(db: Session) -> int:
    agency_ids = drain_pending_agency_rollup_refreshes()
    processed = 0
    for agency_id in agency_ids:
        try:
            refresh_agency_rollups(db, agency_id)
            processed += 1
        except Exception:
            logger.exception("Failed to process queued rollup refresh for agency %s", agency_id)
            db.rollback()
    return processed


def get_or_refresh_dashboard_rollup(db: Session, agency_id: str) -> AgencyDashboardRollup:
    rollup = db.get(AgencyDashboardRollup, agency_id)
    if rollup is None:
        return refresh_agency_dashboard_rollups(db, agency_id)
    return rollup


def get_or_refresh_report_metadata_cache(db: Session, agency_id: str) -> AgencyReportMetadataCache:
    cache = db.get(AgencyReportMetadataCache, agency_id)
    if cache is None:
        return refresh_agency_report_metadata_cache(db, agency_id)
    return cache


def rollup_refresh_triggers_on_cruise_status(status: str) -> bool:
    return status in {
        PROPOSED_CRUISE_STATUS_ACCEPTED,
        PROPOSED_CRUISE_STATUS_DEPOSITED,
        PROPOSED_CRUISE_STATUS_REJECTED,
    }
