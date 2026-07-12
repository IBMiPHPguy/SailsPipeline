from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from statistics import median

from sqlalchemy import String, and_, case, cast, exists, false, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.constants import (
    BOOKED_CRUISE_STATUSES,
    CRUISE_LINES,
    PROPOSED_CRUISE_REJECTION_REASON_OTHER,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    TASK_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
)
from app.models import (
    AgencyTaskTemplate,
    AgencyWorkflowTemplate,
    Passenger,
    ProposedCruise,
    RequestTaskLive,
    RequestWorkflowLive,
    TravelRequest,
    User,
)
from app.schemas import (
    AdvisorScorecardPageRead,
    AdvisorScorecardRowRead,
    FunnelLeakPageRead,
    FunnelLeakRowRead,
    PassengerDemographicsPageRead,
    PassengerDemographicsRowRead,
    ReportManifestRowRead,
    ReportMetaResponse,
    ReportSupplierLedgerRowRead,
    ReportWorkflowTaskGroup,
    ReportWorkflowTaskOption,
    SalesManifestPageRead,
    SupplierLedgerPageRead,
)
from app.services.agency_rollup_service import get_or_refresh_report_metadata_cache
from app.services.booked_cruise_metrics import cruise_total_commission, sum_booked_cruise_financials
from app.services.request_service import resolve_next_open_task
from app.services.request_service import resolve_next_open_task

REPORTS_PAGE_SIZE_DEFAULT = 25
REPORTS_PAGE_SIZE_MAX = 100

ACTIVE_QUOTE_STATUSES = (
    PROPOSED_CRUISE_STATUS_PROPOSED,
    *BOOKED_CRUISE_STATUSES,
)


@dataclass(frozen=True)
class ReportQueryFilters:
    agency_id: str
    cruise_line: str = "all"
    timeframe: str = "all_time"
    pipeline_status: str = "all"
    workflow_task: str = "all"
    rejection_reason: str = "all"
    loss_segment: str = "all"
    advisor: str = "all"
    qualifiers: tuple[str, ...] = ()
    state: str = "all"
    page: int = 1
    page_size: int = REPORTS_PAGE_SIZE_DEFAULT
    owned_by_user_id: int | None = None


def normalize_report_qualifiers(values: list[str]) -> tuple[str, ...]:
    from app.schemas import validate_qualifier_values

    cleaned = [value.strip() for value in values if value and value.strip() and value.strip() != "all"]
    if not cleaned:
        return ()
    unique = tuple(dict.fromkeys(cleaned))
    validate_qualifier_values(list(unique))
    return unique


REJECTION_REASON_NOT_RECORDED = "Reason not recorded"
LOSS_SEGMENT_REJECTED_QUOTE = "rejected_quote"
LOSS_SEGMENT_CLOSED_LOST = "closed_lost"


def _normalize_page(page: int, page_size: int) -> tuple[int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, REPORTS_PAGE_SIZE_MAX))
    offset = (safe_page - 1) * safe_page_size
    return safe_page, safe_page_size, offset


def _pagination_meta(total: int, page: int, page_size: int) -> int:
    if total == 0:
        return 0
    return ceil(total / page_size)


def _reports_query(db: Session, filters: ReportQueryFilters | None = None):
    agency_id = filters.agency_id if filters is not None else None
    query = db.query(TravelRequest).options(
        joinedload(TravelRequest.created_by),
        joinedload(TravelRequest.updated_by),
        selectinload(TravelRequest.proposed_cruises),
        selectinload(TravelRequest.request_workflows_live).selectinload(RequestWorkflowLive.tasks),
    )
    if agency_id is not None:
        query = query.filter(TravelRequest.agency_id == agency_id)
    if filters is not None and filters.owned_by_user_id is not None:
        query = query.filter(TravelRequest.created_by_id == filters.owned_by_user_id)
    if filters is not None:
        query = _apply_travel_request_report_filters(query, filters)
    return query


def _passengers_filtered_query(db: Session, filters: ReportQueryFilters):
    query = db.query(Passenger).filter(
        Passenger.agency_id == filters.agency_id,
        Passenger.is_active.is_(True),
    )

    if filters.state != "all":
        query = query.filter(
            func.lower(func.trim(Passenger.state_or_province)) == filters.state.casefold()
        )

    if filters.qualifiers:
        query = query.filter(
            or_(
                *[
                    cast(Passenger.qualifiers, String).like(f'%"{qualifier}"%')
                    for qualifier in filters.qualifiers
                ]
            )
        )

    return query


def _cruise_total_commission(cruise: ProposedCruise) -> float:
    return float(cruise_total_commission(cruise))


def _timeframe_start(timeframe: str) -> datetime | None:
    today = date.today()
    if timeframe == "current_month":
        return datetime(today.year, today.month, 1)
    if timeframe == "last_30_days":
        return datetime.combine(today - timedelta(days=30), datetime.min.time())
    if timeframe == "current_year":
        return datetime(today.year, 1, 1)
    return None


def _apply_timeframe_filter(query, timeframe: str):
    timeframe_start = _timeframe_start(timeframe)
    if timeframe_start is not None:
        query = query.filter(TravelRequest.created_at >= timeframe_start)
    return query.filter(TravelRequest.created_at.isnot(None))


def _parse_workflow_task_key(workflow_task: str) -> str | None:
    if not workflow_task or workflow_task == "all":
        return None
    if workflow_task.startswith("task:"):
        return workflow_task.split(":", 1)[1]
    return workflow_task


def _first_open_task_key_subquery(agency_id: str):
    return (
        select(RequestTaskLive.task_key)
        .select_from(RequestTaskLive)
        .join(RequestWorkflowLive, RequestTaskLive.request_workflow_live_id == RequestWorkflowLive.id)
        .where(
            RequestTaskLive.agency_id == agency_id,
            RequestWorkflowLive.agency_id == agency_id,
            RequestWorkflowLive.travel_request_id == TravelRequest.id,
            RequestWorkflowLive.status == WORKFLOW_STATUS_ACTIVE,
            RequestTaskLive.status == TASK_STATUS_OPEN,
        )
        .order_by(RequestTaskLive.sequence_order.asc())
        .limit(1)
        .correlate(TravelRequest)
        .scalar_subquery()
    )


def _lead_cruise_line_subquery(agency_id: str):
    return (
        select(ProposedCruise.cruise_line)
        .where(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.travel_request_id == TravelRequest.id,
        )
        .order_by(
            case(
                (ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES), 1),
                (ProposedCruise.status.in_(ACTIVE_QUOTE_STATUSES), 2),
                (ProposedCruise.status == PROPOSED_CRUISE_STATUS_REJECTED, 3),
                else_=4,
            ),
            ProposedCruise.cost.desc(),
        )
        .limit(1)
        .correlate(TravelRequest)
        .scalar_subquery()
    )


def _request_prefers_cruise_line(cruise_line: str):
    return cast(TravelRequest.cruise_lines, String).like(f'%"{cruise_line}"%')


def _apply_cruise_line_filter(query, cruise_line: str, agency_id: str):
    if not cruise_line or cruise_line == "all":
        return query
    if cruise_line not in CRUISE_LINES:
        return query.filter(false())

    lead_line = _lead_cruise_line_subquery(agency_id)
    has_proposed_cruises = exists(
        select(ProposedCruise.id).where(
            ProposedCruise.agency_id == agency_id,
            ProposedCruise.travel_request_id == TravelRequest.id,
        )
    )
    return query.filter(
        or_(
            lead_line == cruise_line,
            and_(~has_proposed_cruises, _request_prefers_cruise_line(cruise_line)),
        )
    )


def _apply_travel_request_report_filters(query, filters: ReportQueryFilters):
    query = query.filter(TravelRequest.agency_id == filters.agency_id)
    query = _apply_timeframe_filter(query, filters.timeframe)

    if filters.pipeline_status == "open":
        query = query.filter(TravelRequest.status == REQUEST_STATUS_OPEN)
    elif filters.pipeline_status == "closed":
        query = query.filter(TravelRequest.status == REQUEST_STATUS_CLOSED)

    task_key = _parse_workflow_task_key(filters.workflow_task)
    if task_key is not None:
        query = query.filter(_first_open_task_key_subquery(filters.agency_id) == task_key)

    return _apply_cruise_line_filter(query, filters.cruise_line, filters.agency_id)


def _apply_proposed_cruise_timeframe_filter(query, timeframe: str):
    timeframe_start = _timeframe_start(timeframe)
    if timeframe_start is not None:
        query = query.filter(ProposedCruise.created_at >= timeframe_start)
    return query.filter(ProposedCruise.created_at.isnot(None))


def _booked_cruises_query(db: Session, filters: ReportQueryFilters):
    query = db.query(ProposedCruise).filter(
        ProposedCruise.agency_id == filters.agency_id,
        ProposedCruise.status.in_(BOOKED_CRUISE_STATUSES),
    )
    if filters.owned_by_user_id is not None:
        query = query.join(
            TravelRequest, TravelRequest.id == ProposedCruise.travel_request_id
        ).filter(TravelRequest.created_by_id == filters.owned_by_user_id)
    query = _apply_proposed_cruise_timeframe_filter(query, filters.timeframe)

    if filters.cruise_line and filters.cruise_line != "all":
        if filters.cruise_line not in CRUISE_LINES:
            return query.filter(false())
        query = query.filter(ProposedCruise.cruise_line == filters.cruise_line)

    return query


def _request_pipeline_bucket(request: TravelRequest) -> str:
    if request.status == REQUEST_STATUS_OPEN:
        return "open"
    return "closed"


def _pipeline_status_label(bucket: str) -> str:
    if bucket == "closed":
        return "Closed"
    return "Open"


def _lead_cruise(cruises: list[ProposedCruise]) -> ProposedCruise | None:
    if not cruises:
        return None

    booked = [cruise for cruise in cruises if cruise.status in BOOKED_CRUISE_STATUSES]
    if booked:
        return max(booked, key=lambda cruise: float(cruise.cost or 0))

    active = [cruise for cruise in cruises if cruise.status in ACTIVE_QUOTE_STATUSES]
    if active:
        return max(active, key=lambda cruise: float(cruise.cost or 0))

    rejected = [cruise for cruise in cruises if cruise.status == PROPOSED_CRUISE_STATUS_REJECTED]
    if rejected:
        return max(rejected, key=lambda cruise: float(cruise.cost or 0))
    return None


def _format_sailing_month_year(departure_date: date | None) -> str:
    if departure_date is None:
        return "—"
    return departure_date.strftime("%b %Y")


def _primary_passenger_name(request: TravelRequest) -> str:
    return f"{request.first_name} {request.last_name}".strip()


def _owner_agent(request: TravelRequest) -> str:
    if request.updated_by is not None:
        return request.updated_by.username
    if request.created_by is not None:
        return request.created_by.username
    return "—"


def _lead_cruise_line(request: TravelRequest, lead_cruise: ProposedCruise | None) -> str:
    if lead_cruise is not None:
        return lead_cruise.cruise_line
    preferred = request.cruise_lines or []
    return preferred[0] if preferred else "—"


def _lead_departure_date(request: TravelRequest, lead_cruise: ProposedCruise | None) -> date | None:
    if lead_cruise is not None:
        return lead_cruise.departure_date
    return request.departure_date


def _build_manifest_row(request: TravelRequest) -> ReportManifestRowRead:
    cruises = list(request.proposed_cruises or [])
    booked_cruises = [cruise for cruise in cruises if cruise.status in BOOKED_CRUISE_STATUSES]
    lead_cruise = _lead_cruise(cruises)
    bucket = _request_pipeline_bucket(request)
    if booked_cruises:
        gross_total, commission_target = sum_booked_cruise_financials(booked_cruises)
        display_cruise = max(booked_cruises, key=lambda cruise: float(cruise.cost or 0))
    else:
        gross_total = float(lead_cruise.cost or 0) if lead_cruise is not None else 0.0
        commission_target = _cruise_total_commission(lead_cruise) if lead_cruise is not None else 0.0
        display_cruise = lead_cruise

    return ReportManifestRowRead(
        request_id=request.id,
        request_status=request.status,
        pipeline_status=_pipeline_status_label(bucket),
        close_reason=request.close_reason,
        primary_passenger=_primary_passenger_name(request),
        destination=request.destination,
        cruise_line=_lead_cruise_line(request, display_cruise),
        sailing_month_year=_format_sailing_month_year(_lead_departure_date(request, display_cruise)),
        estimated_gross_booking_total=gross_total,
        projected_commission_target=commission_target,
        owner_agent=_owner_agent(request),
        current_task=resolve_next_open_task(request),
    )


def _paginate[T](items: list[T], page: int, page_size: int) -> tuple[list[T], int, int, int]:
    page, page_size, _offset = _normalize_page(page, page_size)
    total = len(items)
    total_pages = _pagination_meta(total, page, page_size)
    start = (page - 1) * page_size
    return items[start : start + page_size], total, page, total_pages


def get_report_meta(db: Session, agency_id: str) -> ReportMetaResponse:
    from app.services.workflow_template_seed import seed_agency_workflow_templates

    seed_agency_workflow_templates(db, agency_id)
    db.flush()

    templates = (
        db.query(AgencyWorkflowTemplate)
        .filter(
            AgencyWorkflowTemplate.agency_id == agency_id,
            AgencyWorkflowTemplate.archived_at.is_(None),
        )
        .order_by(AgencyWorkflowTemplate.workflow_name.asc())
        .all()
    )
    workflow_task_groups: list[ReportWorkflowTaskGroup] = []
    for template in templates:
        task_templates = (
            db.query(AgencyTaskTemplate)
            .filter(AgencyTaskTemplate.workflow_template_id == template.id)
            .order_by(AgencyTaskTemplate.sequence_order.asc())
            .all()
        )
        workflow_type = template.workflow_type_key or template.id
        workflow_task_groups.append(
            ReportWorkflowTaskGroup(
                workflow_type=workflow_type,
                workflow_name=template.workflow_name,
                tasks=[
                    ReportWorkflowTaskOption(
                        value=f"task:{task_template.task_key}" if task_template.task_key else f"title:{task_template.task_title}",
                        label=task_template.task_title,
                    )
                    for task_template in task_templates
                ],
            )
        )

    cache = get_or_refresh_report_metadata_cache(db, agency_id)
    advisor_names = list(cache.active_advisor_names or [])
    residence_states = list(cache.active_residence_states or [])

    return ReportMetaResponse(
        workflow_task_groups=workflow_task_groups,
        advisor_names=advisor_names,
        residence_states=residence_states,
    )


def get_sales_manifest_page(db: Session, filters: ReportQueryFilters) -> SalesManifestPageRead:
    page, page_size, offset = _normalize_page(filters.page, filters.page_size)
    base = _reports_query(db, filters)
    total = base.order_by(None).count()
    requests = (
        base.order_by(TravelRequest.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    rows = [_build_manifest_row(request) for request in requests]
    return SalesManifestPageRead(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=_pagination_meta(total, page, page_size),
    )


def _median_booking_amount(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _build_supplier_ledger_rows_from_aggregates(
    aggregates: list[tuple[str, int, float | Decimal | None]],
    cruises: list[ProposedCruise],
) -> list[ReportSupplierLedgerRowRead]:
    commission_by_line: dict[str, Decimal] = {}
    costs_by_line: dict[str, list[float]] = {}
    for cruise in cruises:
        line = (cruise.cruise_line or "Unknown").strip() or "Unknown"
        costs_by_line.setdefault(line, []).append(float(cruise.cost or 0))
        commission_by_line.setdefault(line, Decimal("0"))
        commission_by_line[line] += Decimal(str(_cruise_total_commission(cruise)))

    total_bookings = sum(booking_count for _, booking_count, _ in aggregates)
    rows: list[ReportSupplierLedgerRowRead] = []
    for cruise_line, booking_count, total_volume in sorted(
        aggregates,
        key=lambda row: (-row[1], (row[0] or "Unknown")),
    ):
        line = (cruise_line or "Unknown").strip() or "Unknown"
        total_volume_f = float(total_volume or 0)
        total_commission = float(commission_by_line.get(line, Decimal("0")))
        median_price = _median_booking_amount(costs_by_line.get(line, []))
        commission_rate = round((total_commission / total_volume_f) * 100, 1) if total_volume_f else 0.0
        rows.append(
            ReportSupplierLedgerRowRead(
                cruise_line=line,
                active_booking_count=booking_count,
                total_volume=total_volume_f,
                total_commission_booked=total_commission,
                median_price_per_room=median_price,
                average_commission_rate_percent=commission_rate,
                share_percent=round((booking_count / total_bookings) * 100, 1) if total_bookings else 0.0,
            )
        )
    return rows


def get_supplier_ledger_page(db: Session, filters: ReportQueryFilters) -> SupplierLedgerPageRead:
    base = _booked_cruises_query(db, filters)
    aggregates = (
        base.with_entities(
            ProposedCruise.cruise_line,
            func.count(ProposedCruise.id),
            func.sum(ProposedCruise.cost),
        )
        .group_by(ProposedCruise.cruise_line)
        .all()
    )
    cruises = base.all()
    rows = _build_supplier_ledger_rows_from_aggregates(aggregates, cruises)
    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return SupplierLedgerPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def _booked_request_ids_from(requests: list[TravelRequest]) -> set[int]:
    booked_ids: set[int] = set()
    for request in requests:
        for cruise in request.proposed_cruises or []:
            if cruise.status in BOOKED_CRUISE_STATUSES:
                booked_ids.add(request.id)
                break
    return booked_ids


def _rejection_driver_label(cruise: ProposedCruise) -> str:
    reason = (cruise.rejection_reason or "").strip()
    if not reason:
        return REJECTION_REASON_NOT_RECORDED
    if reason == PROPOSED_CRUISE_REJECTION_REASON_OTHER:
        detail = (cruise.rejection_reason_detail or "").strip()
        return detail or reason
    return reason


def _primary_rejected_cruise(cruises: list[ProposedCruise]) -> ProposedCruise | None:
    rejected = [cruise for cruise in cruises if cruise.status == PROPOSED_CRUISE_STATUS_REJECTED]
    if not rejected:
        return None
    return max(rejected, key=lambda cruise: float(cruise.cost or 0))


def _estimated_value_lost(cruises: list[ProposedCruise]) -> float:
    if not cruises:
        return 0.0
    non_zero_costs = [float(cruise.cost or 0) for cruise in cruises if float(cruise.cost or 0) > 0]
    if not non_zero_costs:
        return 0.0
    if len(cruises) == 1:
        return non_zero_costs[0]
    return float(min(non_zero_costs))


def _funnel_leak_segment(request: TravelRequest, booked_request_ids: set[int]) -> str | None:
    cruises = list(request.proposed_cruises or [])
    has_rejected = any(cruise.status == PROPOSED_CRUISE_STATUS_REJECTED for cruise in cruises)
    is_closed_without_booking = request.status == REQUEST_STATUS_CLOSED and request.id not in booked_request_ids

    if request.status == REQUEST_STATUS_OPEN and has_rejected and request.id not in booked_request_ids:
        return LOSS_SEGMENT_REJECTED_QUOTE
    if is_closed_without_booking:
        return LOSS_SEGMENT_CLOSED_LOST
    return None


def _build_funnel_leak_row(request: TravelRequest, booked_request_ids: set[int]) -> FunnelLeakRowRead | None:
    segment = _funnel_leak_segment(request, booked_request_ids)
    if segment is None:
        return None

    cruises = list(request.proposed_cruises or [])
    rejected_cruise = _primary_rejected_cruise(cruises)
    quoted_cruise = rejected_cruise or _lead_cruise(cruises)
    if rejected_cruise is not None:
        primary_reason = _rejection_driver_label(rejected_cruise)
    else:
        primary_reason = (request.close_reason or "").strip() or REJECTION_REASON_NOT_RECORDED

    return FunnelLeakRowRead(
        request_id=request.id,
        client_name=_primary_passenger_name(request),
        quoted_cruise_line=quoted_cruise.cruise_line if quoted_cruise is not None else _lead_cruise_line(request, quoted_cruise),
        quoted_destination=request.destination,
        estimated_value_lost=_estimated_value_lost(cruises),
        primary_rejection_reason=primary_reason,
        loss_segment=segment,
    )


def _funnel_leak_matches_filters(row: FunnelLeakRowRead, filters: ReportQueryFilters) -> bool:
    if filters.loss_segment != "all" and row.loss_segment != filters.loss_segment:
        return False
    if filters.rejection_reason != "all" and row.primary_rejection_reason != filters.rejection_reason:
        return False
    if filters.cruise_line != "all" and row.quoted_cruise_line != filters.cruise_line:
        return False
    return True


def get_funnel_leak_page(db: Session, filters: ReportQueryFilters) -> FunnelLeakPageRead:
    base = _apply_timeframe_filter(_reports_query(db, filters), filters.timeframe)
    base = base.filter(TravelRequest.agency_id == filters.agency_id)
    requests = base.order_by(TravelRequest.created_at.desc()).all()
    booked_request_ids = _booked_request_ids_from(requests)
    rows: list[FunnelLeakRowRead] = []

    for request in requests:
        row = _build_funnel_leak_row(request, booked_request_ids)
        if row is None:
            continue
        if _funnel_leak_matches_filters(row, filters):
            rows.append(row)

    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return FunnelLeakPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def _request_in_timeframe(request: TravelRequest, timeframe: str) -> bool:
    created_at = request.created_at
    if created_at is None:
        return False
    timeframe_start = _timeframe_start(timeframe)
    if timeframe_start is not None and created_at < timeframe_start:
        return False
    return True


def _build_advisor_scorecard_rows(requests: list[TravelRequest], filters: ReportQueryFilters) -> list[AdvisorScorecardRowRead]:
    scoped_requests = [request for request in requests if _request_in_timeframe(request, filters.timeframe)]
    advisor_names = sorted(
        {_owner_agent(request) for request in scoped_requests if _owner_agent(request) != "—"}
    )

    if filters.advisor != "all":
        advisor_names = [name for name in advisor_names if name == filters.advisor]

    rows: list[AdvisorScorecardRowRead] = []
    for advisor_name in advisor_names:
        owned_requests = [request for request in scoped_requests if _owner_agent(request) == advisor_name]
        active_lead_count = sum(1 for request in owned_requests if request.status == REQUEST_STATUS_OPEN)
        proposals_pending = sum(
            1
            for request in owned_requests
            if request.status == REQUEST_STATUS_OPEN
            and any(cruise.status == PROPOSED_CRUISE_STATUS_PROPOSED for cruise in (request.proposed_cruises or []))
        )

        booked_cruises: list[tuple[TravelRequest, ProposedCruise]] = []
        for request in owned_requests:
            for cruise in request.proposed_cruises or []:
                if cruise.status in BOOKED_CRUISE_STATUSES:
                    booked_cruises.append((request, cruise))

        completed_bookings = len(booked_cruises)
        velocity_days: list[float] = []
        for request, cruise in booked_cruises:
            if request.created_at is None or cruise.updated_at is None:
                continue
            delta = cruise.updated_at - request.created_at
            velocity_days.append(max(delta.total_seconds(), 0) / 86400)

        avg_pipeline_velocity_days = round(sum(velocity_days) / len(velocity_days), 1) if velocity_days else None
        booked_request_ids = {request.id for request, _cruise in booked_cruises}
        request_to_close_ratio_percent = (
            round((len(booked_request_ids) / len(owned_requests)) * 100, 1) if owned_requests else None
        )

        rows.append(
            AdvisorScorecardRowRead(
                advisor_name=advisor_name,
                active_lead_count=active_lead_count,
                proposals_pending=proposals_pending,
                completed_bookings=completed_bookings,
                avg_pipeline_velocity_days=avg_pipeline_velocity_days,
                request_to_close_ratio_percent=request_to_close_ratio_percent,
            )
        )

    rows.sort(key=lambda row: (-row.completed_bookings, -row.active_lead_count, row.advisor_name))
    return rows


def get_advisor_scorecard_page(db: Session, filters: ReportQueryFilters) -> AdvisorScorecardPageRead:
    base = _apply_timeframe_filter(_reports_query(db, filters), filters.timeframe)
    base = base.filter(TravelRequest.agency_id == filters.agency_id)
    requests = base.all()
    rows = _build_advisor_scorecard_rows(requests, filters)
    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return AdvisorScorecardPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def get_passenger_demographics_page(db: Session, filters: ReportQueryFilters) -> PassengerDemographicsPageRead:
    page, page_size, offset = _normalize_page(filters.page, filters.page_size)
    base = _passengers_filtered_query(db, filters)
    total = base.order_by(None).count()
    passengers = (
        base.order_by(Passenger.last_name.asc(), Passenger.first_name.asc(), Passenger.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    rows = [
        PassengerDemographicsRowRead(
            passenger_id=passenger.id,
            passenger_name=f"{passenger.first_name} {passenger.last_name}".strip(),
            date_of_birth=passenger.date_of_birth.isoformat() if passenger.date_of_birth else None,
            state_of_residence=passenger.state_or_province,
            contact_phone=passenger.phone,
            email_address=passenger.email,
            qualifiers=list(passenger.qualifiers or []),
        )
        for passenger in passengers
    ]
    return PassengerDemographicsPageRead(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=_pagination_meta(total, page, page_size),
    )
