from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    AdvisorScorecardPageRead,
    FunnelLeakPageRead,
    PassengerDemographicsPageRead,
    ReportMetaResponse,
    SalesManifestPageRead,
    SupplierLedgerPageRead,
)
from app.services.agent_capability_service import get_capabilities_for_user
from app.services.reports_service import (
    ReportQueryFilters,
    normalize_report_qualifiers,
    get_advisor_scorecard_page,
    get_funnel_leak_page,
    get_passenger_demographics_page,
    get_report_meta,
    get_sales_manifest_page,
    get_supplier_ledger_page,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _filters_from_query(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cruise_line: str = Query(default="all"),
    timeframe: str = Query(default="all_time"),
    pipeline_status: str = Query(default="all"),
    workflow_task: str = Query(default="all"),
    rejection_reason: str = Query(default="all"),
    loss_segment: str = Query(default="all"),
    advisor: str = Query(default="all"),
    qualifier: list[str] = Query(default=[]),
    state: str = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> ReportQueryFilters:
    caps = get_capabilities_for_user(db, current_user)
    owned_by_user_id = current_user.id if caps.reports_own_only else None
    return ReportQueryFilters(
        agency_id=current_user.agency_id,
        cruise_line=cruise_line,
        timeframe=timeframe,
        pipeline_status=pipeline_status,
        workflow_task=workflow_task,
        rejection_reason=rejection_reason,
        loss_segment=loss_segment,
        advisor=advisor,
        qualifiers=normalize_report_qualifiers(qualifier),
        state=state.strip() or "all",
        page=page,
        page_size=page_size,
        owned_by_user_id=owned_by_user_id,
    )


@router.get("/meta", response_model=ReportMetaResponse)
def get_reports_meta_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportMetaResponse:
    return get_report_meta(db, current_user.agency_id)


@router.get("/sales-manifest", response_model=SalesManifestPageRead)
def get_sales_manifest_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    filters: ReportQueryFilters = Depends(_filters_from_query),
) -> SalesManifestPageRead:
    return get_sales_manifest_page(db, filters)


@router.get("/supplier-ledger", response_model=SupplierLedgerPageRead)
def get_supplier_ledger_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    filters: ReportQueryFilters = Depends(_filters_from_query),
) -> SupplierLedgerPageRead:
    return get_supplier_ledger_page(db, filters)


@router.get("/funnel-leak", response_model=FunnelLeakPageRead)
def get_funnel_leak_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    filters: ReportQueryFilters = Depends(_filters_from_query),
) -> FunnelLeakPageRead:
    return get_funnel_leak_page(db, filters)


@router.get("/advisor-scorecard", response_model=AdvisorScorecardPageRead)
def get_advisor_scorecard_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    filters: ReportQueryFilters = Depends(_filters_from_query),
) -> AdvisorScorecardPageRead:
    return get_advisor_scorecard_page(db, filters)


@router.get("/passenger-demographics", response_model=PassengerDemographicsPageRead)
def get_passenger_demographics_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    filters: ReportQueryFilters = Depends(_filters_from_query),
) -> PassengerDemographicsPageRead:
    return get_passenger_demographics_page(db, filters)
