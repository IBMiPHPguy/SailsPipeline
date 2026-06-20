from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from math import ceil
from statistics import median

from sqlalchemy.orm import Session, joinedload, selectinload

from app.constants import (
    CRUISE_LINES,
    PROPOSED_CRUISE_REJECTION_REASON_OTHER,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    WORKFLOW_STATUS_ACTIVE,
    TASK_STATUS_OPEN,
)
from app.models import Passenger, ProposedCruise, RequestWorkflow, TravelRequest
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
from app.services.request_service import resolve_next_open_task
from app.workflow_helpers import WORKFLOW_DEFINITIONS, WORKFLOW_TASK_TEMPLATES, get_workflow_label

REPORTS_PAGE_SIZE_DEFAULT = 25
REPORTS_PAGE_SIZE_MAX = 100

BOOKED_CRUISE_STATUSES = (
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
)

ACTIVE_QUOTE_STATUSES = (
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
)


@dataclass(frozen=True)
class ReportQueryFilters:
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


def _reports_query(db: Session):
    return db.query(TravelRequest).options(
        joinedload(TravelRequest.created_by),
        joinedload(TravelRequest.updated_by),
        selectinload(TravelRequest.proposed_cruises),
        selectinload(TravelRequest.request_workflows).selectinload(RequestWorkflow.tasks),
    )


def _cruise_total_commission(cruise: ProposedCruise) -> float:
    total = Decimal("0")
    for room in cruise.cabin_rooms or []:
        if not isinstance(room, dict):
            continue
        try:
            total += Decimal(str(room.get("commission") or 0))
        except Exception:
            continue
    return float(total)


def _timeframe_start(timeframe: str) -> datetime | None:
    today = date.today()
    if timeframe == "current_month":
        return datetime(today.year, today.month, 1)
    if timeframe == "last_30_days":
        return datetime.combine(today - timedelta(days=30), datetime.min.time())
    if timeframe == "current_year":
        return datetime(today.year, 1, 1)
    return None


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


def _matches_supplier_filter(
    request: TravelRequest,
    lead_cruise: ProposedCruise | None,
    cruise_line: str,
) -> bool:
    if not cruise_line or cruise_line == "all":
        return True

    if cruise_line not in CRUISE_LINES:
        return False

    if lead_cruise is not None:
        return lead_cruise.cruise_line == cruise_line

    preferred_lines = request.cruise_lines or []
    return cruise_line in preferred_lines


def _matches_workflow_task(request: TravelRequest, workflow_task: str) -> bool:
    if not workflow_task or workflow_task == "all":
        return True

    task_key = workflow_task.split(":", 1)[1] if workflow_task.startswith("task:") else workflow_task

    active_workflow = next(
        (workflow for workflow in request.request_workflows if workflow.status == WORKFLOW_STATUS_ACTIVE),
        None,
    )
    if active_workflow is None:
        return False

    open_tasks = sorted(
        (task for task in active_workflow.tasks if task.status == TASK_STATUS_OPEN),
        key=lambda task: task.sort_order,
    )
    if not open_tasks:
        return False
    return open_tasks[0].task_key == task_key


def _supplier_ledger_request_matches_filters(request: TravelRequest, filters: ReportQueryFilters) -> bool:
    created_at = request.created_at
    if created_at is None:
        return False

    timeframe_start = _timeframe_start(filters.timeframe)
    if timeframe_start is not None and created_at < timeframe_start:
        return False

    deposited_cruises = [
        cruise
        for cruise in (request.proposed_cruises or [])
        if cruise.status == PROPOSED_CRUISE_STATUS_DEPOSITED
    ]
    if not deposited_cruises:
        return False

    if filters.cruise_line and filters.cruise_line != "all":
        if filters.cruise_line not in CRUISE_LINES:
            return False
        return any(cruise.cruise_line == filters.cruise_line for cruise in deposited_cruises)

    return True


def _request_matches_filters(request: TravelRequest, filters: ReportQueryFilters) -> bool:
    created_at = request.created_at
    if created_at is None:
        return False

    timeframe_start = _timeframe_start(filters.timeframe)
    if timeframe_start is not None and created_at < timeframe_start:
        return False

    cruises = list(request.proposed_cruises or [])
    bucket = _request_pipeline_bucket(request)
    if filters.pipeline_status != "all" and bucket != filters.pipeline_status:
        return False

    lead_cruise = _lead_cruise(cruises)
    if not _matches_supplier_filter(request, lead_cruise, filters.cruise_line):
        return False

    if not _matches_workflow_task(request, filters.workflow_task):
        return False

    return True


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
    lead_cruise = _lead_cruise(cruises)
    bucket = _request_pipeline_bucket(request)
    gross_total = float(lead_cruise.cost or 0) if lead_cruise is not None else 0.0
    commission_target = _cruise_total_commission(lead_cruise) if lead_cruise is not None else 0.0

    return ReportManifestRowRead(
        request_id=request.id,
        request_status=request.status,
        pipeline_status=_pipeline_status_label(bucket),
        close_reason=request.close_reason,
        primary_passenger=_primary_passenger_name(request),
        destination=request.destination,
        cruise_line=_lead_cruise_line(request, lead_cruise),
        sailing_month_year=_format_sailing_month_year(_lead_departure_date(request, lead_cruise)),
        estimated_gross_booking_total=gross_total,
        projected_commission_target=commission_target,
        owner_agent=_owner_agent(request),
        current_task=resolve_next_open_task(request),
    )


def _paginate[T](items: list[T], page: int, page_size: int) -> tuple[list[T], int, int, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, REPORTS_PAGE_SIZE_MAX))
    total = len(items)
    total_pages = 0 if total == 0 else ceil(total / page_size)
    start = (page - 1) * page_size
    return items[start : start + page_size], total, page, total_pages


def get_report_meta(db: Session) -> ReportMetaResponse:
    workflow_task_groups: list[ReportWorkflowTaskGroup] = []
    for workflow_type in WORKFLOW_DEFINITIONS:
        templates = sorted(
            WORKFLOW_TASK_TEMPLATES.get(workflow_type, []),
            key=lambda template: template.sort_order,
        )
        workflow_task_groups.append(
            ReportWorkflowTaskGroup(
                workflow_type=workflow_type,
                workflow_name=get_workflow_label(workflow_type),
                tasks=[
                    ReportWorkflowTaskOption(
                        value=f"task:{template.task_key}",
                        label=template.title,
                    )
                    for template in templates
                ],
            )
        )

    requests = _reports_query(db).all()
    advisor_names = sorted(
        {_owner_agent(request) for request in requests if _owner_agent(request) != "—"}
    )
    residence_states = sorted(
        {
            passenger.state_or_province.strip()
            for passenger in db.query(Passenger).filter(Passenger.is_active.is_(True)).all()
            if passenger.state_or_province and passenger.state_or_province.strip()
        }
    )

    return ReportMetaResponse(
        workflow_task_groups=workflow_task_groups,
        advisor_names=advisor_names,
        residence_states=residence_states,
    )


def get_sales_manifest_page(db: Session, filters: ReportQueryFilters) -> SalesManifestPageRead:
    requests = _reports_query(db).order_by(TravelRequest.created_at.desc()).all()
    matching = [request for request in requests if _request_matches_filters(request, filters)]
    rows = [_build_manifest_row(request) for request in matching]
    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return SalesManifestPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def _median_booking_amount(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(median(values))


def _build_supplier_ledger_rows(
    requests: list[TravelRequest],
    cruise_line: str = "all",
) -> list[ReportSupplierLedgerRowRead]:
    costs_by_line: dict[str, list[float]] = {}
    commission_by_line: dict[str, Decimal] = {}

    for request in requests:
        for cruise in request.proposed_cruises or []:
            if cruise.status != PROPOSED_CRUISE_STATUS_DEPOSITED:
                continue
            line = (cruise.cruise_line or "Unknown").strip() or "Unknown"
            if cruise_line != "all" and line != cruise_line:
                continue
            costs_by_line.setdefault(line, []).append(float(cruise.cost or 0))
            commission_by_line.setdefault(line, Decimal("0"))
            commission_by_line[line] += Decimal(str(_cruise_total_commission(cruise)))

    total_bookings = sum(len(costs) for costs in costs_by_line.values())
    rows: list[ReportSupplierLedgerRowRead] = []
    for line in sorted(costs_by_line.keys(), key=lambda name: (-len(costs_by_line[name]), name)):
        costs = costs_by_line[line]
        booking_count = len(costs)
        total_volume = float(sum(costs))
        total_commission = float(commission_by_line[line])
        median_price = _median_booking_amount(costs)
        commission_rate = round((total_commission / total_volume) * 100, 1) if total_volume else 0.0
        rows.append(
            ReportSupplierLedgerRowRead(
                cruise_line=line,
                active_booking_count=booking_count,
                total_volume=total_volume,
                total_commission_booked=total_commission,
                median_price_per_room=median_price,
                average_commission_rate_percent=commission_rate,
                share_percent=round((booking_count / total_bookings) * 100, 1) if total_bookings else 0.0,
            )
        )
    return rows


def get_supplier_ledger_page(db: Session, filters: ReportQueryFilters) -> SupplierLedgerPageRead:
    requests = _reports_query(db).order_by(TravelRequest.created_at.desc()).all()
    matching = [request for request in requests if _supplier_ledger_request_matches_filters(request, filters)]
    rows = _build_supplier_ledger_rows(matching, filters.cruise_line)
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
    requests = _reports_query(db).order_by(TravelRequest.created_at.desc()).all()
    booked_request_ids = _booked_request_ids_from(requests)
    rows: list[FunnelLeakRowRead] = []

    for request in requests:
        created_at = request.created_at
        if created_at is None:
            continue
        timeframe_start = _timeframe_start(filters.timeframe)
        if timeframe_start is not None and created_at < timeframe_start:
            continue

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

        deposited_cruises: list[tuple[TravelRequest, ProposedCruise]] = []
        for request in owned_requests:
            for cruise in request.proposed_cruises or []:
                if cruise.status == PROPOSED_CRUISE_STATUS_DEPOSITED:
                    deposited_cruises.append((request, cruise))

        completed_bookings = len(deposited_cruises)
        velocity_days: list[float] = []
        for request, cruise in deposited_cruises:
            if request.created_at is None or cruise.updated_at is None:
                continue
            delta = cruise.updated_at - request.created_at
            velocity_days.append(max(delta.total_seconds(), 0) / 86400)

        avg_pipeline_velocity_days = round(sum(velocity_days) / len(velocity_days), 1) if velocity_days else None
        deposited_request_ids = {request.id for request, _cruise in deposited_cruises}
        request_to_close_ratio_percent = (
            round((len(deposited_request_ids) / len(owned_requests)) * 100, 1) if owned_requests else None
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
    requests = _reports_query(db).all()
    rows = _build_advisor_scorecard_rows(requests, filters)
    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return AdvisorScorecardPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


def _passenger_matches_filters(passenger: Passenger, filters: ReportQueryFilters) -> bool:
    if not passenger.is_active:
        return False

    if filters.qualifiers:
        passenger_qualifiers = set(passenger.qualifiers or [])
        if not passenger_qualifiers.intersection(filters.qualifiers):
            return False

    if filters.state != "all":
        passenger_state = (passenger.state_or_province or "").strip()
        if passenger_state.casefold() != filters.state.casefold():
            return False

    return True


def get_passenger_demographics_page(db: Session, filters: ReportQueryFilters) -> PassengerDemographicsPageRead:
    passengers = db.query(Passenger).order_by(Passenger.last_name.asc(), Passenger.first_name.asc()).all()
    rows: list[PassengerDemographicsRowRead] = []

    for passenger in passengers:
        if not _passenger_matches_filters(passenger, filters):
            continue
        rows.append(
            PassengerDemographicsRowRead(
                passenger_id=passenger.id,
                passenger_name=f"{passenger.first_name} {passenger.last_name}".strip(),
                date_of_birth=passenger.date_of_birth.isoformat() if passenger.date_of_birth else None,
                state_of_residence=passenger.state_or_province,
                contact_phone=passenger.phone,
                email_address=passenger.email,
                qualifiers=list(passenger.qualifiers or []),
            )
        )

    page_items, total, page, total_pages = _paginate(rows, filters.page, filters.page_size)
    return PassengerDemographicsPageRead(
        items=page_items,
        total=total,
        page=page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )
