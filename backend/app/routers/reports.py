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
    return ReportQueryFilters(
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
    )


@router.get("/meta", response_model=ReportMetaResponse)
def get_reports_meta_route(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ReportMetaResponse:
    return get_report_meta(db)


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
