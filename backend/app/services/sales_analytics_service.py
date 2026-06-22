from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from statistics import median

from sqlalchemy.orm import Session

from app.constants import (
    BOOKED_CRUISE_STATUSES,
    PROPOSED_CRUISE_REJECTION_REASON_OTHER,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    SALES_REJECTION_SEGMENT_CLOSED_LOST,
    SALES_REJECTION_SEGMENT_OPEN_ACTIVE,
)
from app.models import ProposedCruise, TravelRequest, TravelRequestAudit
from app.schemas import (
    SalesAnalyticsCruiseLineShare,
    SalesAnalyticsFunnelStage,
    SalesAnalyticsMonthCommission,
    SalesAnalyticsRejectionReason,
    SalesAnalyticsResponse,
    SalesAnalyticsYearSummary,
)
from app.services.booked_cruise_metrics import cruise_total_commission, load_booked_cruises


REJECTION_REASON_NOT_RECORDED = "Reason not recorded"


def _month_key(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _month_label(value: date) -> str:
    return value.strftime("%b %Y")


def _event_year(value: datetime) -> int:
    return value.year


def _request_close_years(db: Session, request_ids: set[int], agency_id: str) -> dict[int, int]:
    if not request_ids:
        return {}

    close_years: dict[int, int] = {}
    audits = (
        db.query(TravelRequestAudit.travel_request_id, TravelRequestAudit.changed_at)
        .join(TravelRequest, TravelRequest.id == TravelRequestAudit.travel_request_id)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequestAudit.travel_request_id.in_(request_ids),
            TravelRequestAudit.field_name == "status",
            TravelRequestAudit.to_value == REQUEST_STATUS_CLOSED,
        )
        .order_by(TravelRequestAudit.changed_at.asc())
        .all()
    )
    for request_id, changed_at in audits:
        if request_id not in close_years:
            close_years[request_id] = _event_year(changed_at)

    missing_ids = request_ids - close_years.keys()
    if missing_ids:
        for request_id, updated_at in (
            db.query(TravelRequest.id, TravelRequest.updated_at)
            .filter(
                TravelRequest.agency_id == agency_id,
                TravelRequest.id.in_(missing_ids),
                TravelRequest.status == REQUEST_STATUS_CLOSED,
            )
            .all()
        ):
            close_years[request_id] = _event_year(updated_at)

    return close_years


def _booked_request_ids(db: Session, agency_id: str) -> set[int]:
    return {
        row[0]
        for row in db.query(ProposedCruise.travel_request_id)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
        )
        .distinct()
        .all()
    }


def _calculate_closed_win_rate_percent(
    *,
    closed_request_ids: set[int],
    booked_request_ids: set[int],
) -> float | None:
    """Closed requests with a booked proposal divided by all closed requests."""
    if not closed_request_ids:
        return None
    won_request_count = len(closed_request_ids & booked_request_ids)
    return round((won_request_count / len(closed_request_ids)) * 100, 1)


def _calculate_year_closed_win_rate_percent(
    *,
    year: int,
    close_years: dict[int, int],
    booked_request_ids: set[int],
) -> float | None:
    closed_in_year = {request_id for request_id, close_year in close_years.items() if close_year == year}
    return _calculate_closed_win_rate_percent(
        closed_request_ids=closed_in_year,
        booked_request_ids=booked_request_ids,
    )


def _proposed_cruise_total_cost(cruise: ProposedCruise) -> float:
    return float(cruise.cost or 0)


def _closed_lost_sales_amount(proposed_cruises: list[ProposedCruise]) -> float | None:
    if not proposed_cruises:
        return None

    non_zero_costs = [
        cost for cost in (_proposed_cruise_total_cost(cruise) for cruise in proposed_cruises) if cost > 0
    ]
    if not non_zero_costs:
        return None
    if len(proposed_cruises) == 1:
        return non_zero_costs[0]
    return min(non_zero_costs)


def _calculate_year_lost_sales(
    *,
    year: int,
    close_years: dict[int, int],
    booked_request_ids: set[int],
    proposed_cruises_by_request: dict[int, list[ProposedCruise]],
) -> float:
    total_sales_lost = 0.0
    for request_id, close_year in close_years.items():
        if close_year != year or request_id in booked_request_ids:
            continue
        lost_amount = _closed_lost_sales_amount(proposed_cruises_by_request.get(request_id, []))
        if lost_amount is not None:
            total_sales_lost += lost_amount
    return total_sales_lost


def _proposed_cruises_by_request(proposed_cruises: list[ProposedCruise]) -> dict[int, list[ProposedCruise]]:
    grouped: dict[int, list[ProposedCruise]] = defaultdict(list)
    for cruise in proposed_cruises:
        grouped[cruise.travel_request_id].append(cruise)
    return grouped


def _rejection_driver_label(cruise: ProposedCruise) -> str:
    reason = (cruise.rejection_reason or "").strip()
    if not reason:
        return REJECTION_REASON_NOT_RECORDED
    if reason == PROPOSED_CRUISE_REJECTION_REASON_OTHER:
        detail = (cruise.rejection_reason_detail or "").strip()
        return detail or reason
    return reason


def _median_booking_amount(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _build_cruise_line_shares(booked_cruises: list[ProposedCruise]) -> list[SalesAnalyticsCruiseLineShare]:
    costs_by_line: dict[str, list[float]] = defaultdict(list)
    commission_by_line: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for cruise in booked_cruises:
        line = (cruise.cruise_line or "Unknown").strip() or "Unknown"
        costs_by_line[line].append(float(cruise.cost or 0))
        commission_by_line[line] += cruise_total_commission(cruise)

    total_booked = sum(len(costs) for costs in costs_by_line.values())
    shares: list[SalesAnalyticsCruiseLineShare] = []
    for line in sorted(costs_by_line.keys(), key=lambda name: (-len(costs_by_line[name]), name)):
        costs = costs_by_line[line]
        booking_count = len(costs)
        total_booking_amount = float(sum(costs))
        total_commission = float(commission_by_line[line])
        median_booking_amount = _median_booking_amount(costs)
        commission_rate_percent = (
            round((total_commission / total_booking_amount) * 100, 1) if total_booking_amount else 0.0
        )
        shares.append(
            SalesAnalyticsCruiseLineShare(
                cruise_line=line,
                booking_count=booking_count,
                share_percent=round((booking_count / total_booked) * 100, 1) if total_booked else 0.0,
                total_booking_amount=total_booking_amount,
                total_commission=total_commission,
                median_booking_amount=median_booking_amount,
                commission_rate_percent=commission_rate_percent,
            )
        )
    return shares


def _build_rejection_reasons(
    rejected_cruises: list[ProposedCruise],
    *,
    open_request_ids: set[int],
    closed_without_booking_ids: set[int],
) -> list[SalesAnalyticsRejectionReason]:
    open_active_counts: dict[str, int] = defaultdict(int)
    closed_lost_counts: dict[str, int] = defaultdict(int)

    for cruise in rejected_cruises:
        request_id = cruise.travel_request_id
        label = _rejection_driver_label(cruise)
        if request_id in open_request_ids:
            open_active_counts[label] += 1
        elif request_id in closed_without_booking_ids:
            closed_lost_counts[label] += 1

    rejection_reasons: list[SalesAnalyticsRejectionReason] = []
    for reason, count in sorted(open_active_counts.items(), key=lambda item: (-item[1], item[0])):
        rejection_reasons.append(
            SalesAnalyticsRejectionReason(
                segment=SALES_REJECTION_SEGMENT_OPEN_ACTIVE,
                reason=reason,
                count=count,
            )
        )
    for reason, count in sorted(closed_lost_counts.items(), key=lambda item: (-item[1], item[0])):
        rejection_reasons.append(
            SalesAnalyticsRejectionReason(
                segment=SALES_REJECTION_SEGMENT_CLOSED_LOST,
                reason=reason,
                count=count,
            )
        )
    return rejection_reasons


def _load_booked_cruises(db: Session, agency_id: str) -> list[ProposedCruise]:
    return load_booked_cruises(db, agency_id)


def _build_year_summary(
    *,
    year: int,
    booked_cruises: list[ProposedCruise],
    close_years: dict[int, int],
    booked_request_ids: set[int],
    proposed_cruises_by_request: dict[int, list[ProposedCruise]],
) -> SalesAnalyticsYearSummary:
    total_sales_booked = 0.0
    total_commission = Decimal("0")

    for cruise in booked_cruises:
        if _event_year(cruise.updated_at) != year:
            continue
        total_sales_booked += float(cruise.cost or 0)
        total_commission += cruise_total_commission(cruise)

    total_sales_lost = _calculate_year_lost_sales(
        year=year,
        close_years=close_years,
        booked_request_ids=booked_request_ids,
        proposed_cruises_by_request=proposed_cruises_by_request,
    )

    average_commission_rate_percent = (
        round((float(total_commission) / total_sales_booked) * 100, 1) if total_sales_booked else None
    )
    win_rate_percent = _calculate_year_closed_win_rate_percent(
        year=year,
        close_years=close_years,
        booked_request_ids=booked_request_ids,
    )
    return SalesAnalyticsYearSummary(
        year=year,
        total_sales_booked=total_sales_booked,
        total_sales_lost=total_sales_lost,
        average_commission_rate_percent=average_commission_rate_percent,
        win_rate_percent=win_rate_percent,
    )


def _key_metrics_prior_years(
    *,
    booked_cruises: list[ProposedCruise],
    rejected_cruises: list[ProposedCruise],
    close_years: dict[int, int],
    current_year: int,
) -> list[int]:
    years: set[int] = set()
    for cruise in booked_cruises:
        years.add(_event_year(cruise.updated_at))
    for cruise in rejected_cruises:
        years.add(_event_year(cruise.updated_at))
    years.update(close_years.values())
    return sorted(value for value in years if value < current_year)


def _load_key_metrics_source_data(
    db: Session,
    agency_id: str,
) -> tuple[list[ProposedCruise], list[ProposedCruise], set[int], set[int], dict[int, int], dict[int, list[ProposedCruise]]]:
    booked_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
        )
        .all()
    )
    rejected_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_REJECTED,
        )
        .all()
    )
    all_proposed_cruises = db.query(ProposedCruise).filter(ProposedCruise.agency_id == agency_id).all()
    booked_request_ids = _booked_request_ids(db, agency_id)
    closed_request_ids = {
        row[0]
        for row in db.query(TravelRequest.id)
        .filter(
            TravelRequest.agency_id == agency_id,
            TravelRequest.status == REQUEST_STATUS_CLOSED,
        )
        .all()
    }
    closed_without_booking_ids = closed_request_ids - booked_request_ids
    close_years = _request_close_years(db, closed_request_ids, agency_id)
    return (
        booked_cruises,
        rejected_cruises,
        closed_without_booking_ids,
        booked_request_ids,
        close_years,
        _proposed_cruises_by_request(all_proposed_cruises),
    )


def get_sales_analytics_key_metrics_year(db: Session, year: int, agency_id: str) -> SalesAnalyticsYearSummary:
    today = date.today()
    if year > today.year:
        raise ValueError(f"Key metrics are not available for future year {year}.")

    booked_cruises, rejected_cruises, _closed_without_booking_ids, booked_request_ids, close_years, proposed_cruises_by_request = (
        _load_key_metrics_source_data(db, agency_id)
    )
    booked_cruises = _load_booked_cruises(db, agency_id)
    return _build_year_summary(
        year=year,
        booked_cruises=booked_cruises,
        close_years=close_years,
        booked_request_ids=booked_request_ids,
        proposed_cruises_by_request=proposed_cruises_by_request,
    )


def get_sales_analytics(db: Session, agency_id: str) -> SalesAnalyticsResponse:
    today = date.today()

    commission_by_month: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    bookings_by_month: dict[str, int] = defaultdict(int)

    booked_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
        )
        .all()
    )
    for cruise in booked_cruises:
        month = date(cruise.departure_date.year, cruise.departure_date.month, 1)
        key = _month_key(month)
        commission_by_month[key] += cruise_total_commission(cruise)
        bookings_by_month[key] += 1

    timeline_keys = sorted(commission_by_month.keys())
    commission_timeline = [
        SalesAnalyticsMonthCommission(
            month_key=key,
            label=_month_label(date(int(key[:4]), int(key[5:7]), 1)),
            total_commission=float(commission_by_month.get(key, Decimal("0"))),
            booking_count=bookings_by_month.get(key, 0),
        )
        for key in timeline_keys
    ]

    data_years = {int(key[:4]) for key in timeline_keys}
    available_years = sorted(data_years | {today.year, today.year + 1})

    open_requests = (
        db.query(TravelRequest)
        .filter(TravelRequest.agency_id == agency_id, TravelRequest.status == REQUEST_STATUS_OPEN)
        .count()
    )
    open_request_ids = {
        row[0]
        for row in db.query(TravelRequest.id)
        .filter(TravelRequest.agency_id == agency_id, TravelRequest.status == REQUEST_STATUS_OPEN)
        .all()
    }
    quoted_requests = (
        db.query(ProposedCruise.travel_request_id)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.travel_request_id.in_(open_request_ids),
        )
        .distinct()
        .count()
    )
    proposed_cruise_count = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.travel_request_id.in_(open_request_ids),
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_PROPOSED,
        )
        .count()
    )
    accepted_count = db.query(ProposedCruise).filter(
        ProposedCruise.agency_id == agency_id,
        ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
    ).count()
    rejected_count = db.query(ProposedCruise).filter(
        ProposedCruise.agency_id == agency_id,
        ProposedCruise.status == PROPOSED_CRUISE_STATUS_REJECTED,
    ).count()

    booked_request_ids = _booked_request_ids(db, agency_id)
    closed_request_ids = {
        row[0]
        for row in db.query(TravelRequest.id)
        .filter(TravelRequest.agency_id == agency_id, TravelRequest.status == REQUEST_STATUS_CLOSED)
        .all()
    }
    closed_without_booking_ids = closed_request_ids - booked_request_ids
    close_years = _request_close_years(db, closed_request_ids, agency_id)
    win_rate_percent = _calculate_closed_win_rate_percent(
        closed_request_ids=closed_request_ids,
        booked_request_ids=booked_request_ids,
    )

    funnel_stages = [
        SalesAnalyticsFunnelStage(label="Active leads", count=open_requests),
        SalesAnalyticsFunnelStage(label="Quoted requests", count=quoted_requests),
        SalesAnalyticsFunnelStage(label="Proposals pending", count=proposed_cruise_count),
        SalesAnalyticsFunnelStage(label="Accepted bookings", count=accepted_count),
        SalesAnalyticsFunnelStage(label="Rejected quotes", count=rejected_count),
    ]

    rejected_cruises = (
        db.query(ProposedCruise)
        .filter(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.status == PROPOSED_CRUISE_STATUS_REJECTED,
        )
        .all()
    )
    rejection_reasons = _build_rejection_reasons(
        rejected_cruises,
        open_request_ids=open_request_ids,
        closed_without_booking_ids=closed_without_booking_ids,
    )

    booked_cruises_for_shares = _load_booked_cruises(db, agency_id)
    cruise_line_shares = _build_cruise_line_shares(booked_cruises_for_shares)
    proposed_cruises_by_request = _proposed_cruises_by_request(
        db.query(ProposedCruise).filter(ProposedCruise.agency_id == agency_id).all()
    )

    current_year_summary = _build_year_summary(
        year=today.year,
        booked_cruises=booked_cruises_for_shares,
        close_years=close_years,
        booked_request_ids=booked_request_ids,
        proposed_cruises_by_request=proposed_cruises_by_request,
    )
    key_metrics_prior_years = _key_metrics_prior_years(
        booked_cruises=booked_cruises_for_shares,
        rejected_cruises=rejected_cruises,
        close_years=close_years,
        current_year=today.year,
    )

    total_commission_forecast = float(sum(commission_by_month.values()))

    return SalesAnalyticsResponse(
        commission_timeline=commission_timeline,
        funnel_stages=funnel_stages,
        win_rate_percent=win_rate_percent,
        rejection_reasons=rejection_reasons,
        cruise_line_shares=cruise_line_shares,
        current_year_summary=current_year_summary,
        key_metrics_prior_years=key_metrics_prior_years,
        total_commission_forecast=total_commission_forecast,
        available_years=available_years,
    )
