from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import (
    ClientImportParseResponse,
    ClientImportResultResponse,
    SalesAnalyticsResponse,
    SalesAnalyticsYearSummary,
    SalesCopilotRequest,
    SalesCopilotResponse,
)
from app.services.client_import_parse_service import parse_client_import_upload
from app.services.client_import_service import execute_client_import
from app.services.client_import_template_service import (
    CLIENT_IMPORT_TEMPLATE_FILENAME,
    build_client_import_template_xlsx,
)
from app.services.sales_analytics_copilot_service import answer_sales_copilot_question
from app.services.sales_analytics_service import get_sales_analytics, get_sales_analytics_key_metrics_year
from app.gemini_service import GeminiConfigurationError, GeminiParseError

router = APIRouter(prefix="/api/analytics/sales", tags=["sales-analytics"])


@router.get("", response_model=SalesAnalyticsResponse)
def get_sales_analytics_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesAnalyticsResponse:
    return get_sales_analytics(db, current_user.agency_id)


@router.get("/key-metrics/{year}", response_model=SalesAnalyticsYearSummary)
def get_sales_analytics_key_metrics_route(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesAnalyticsYearSummary:
    try:
        return get_sales_analytics_key_metrics_year(db, year, current_user.agency_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/client-import/template")
def download_client_import_template_route(
    _: User = Depends(get_current_user),
) -> Response:
    try:
        content = build_client_import_template_xlsx()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{CLIENT_IMPORT_TEMPLATE_FILENAME}"'},
    )


@router.post("/client-import/parse", response_model=ClientImportParseResponse)
async def parse_client_import_file_route(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
) -> ClientImportParseResponse:
    content = await file.read()
    filename = file.filename or "upload"
    try:
        result = parse_client_import_upload(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ClientImportParseResponse(**result)


@router.post("/client-import", response_model=ClientImportResultResponse)
async def import_client_spreadsheet_route(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientImportResultResponse:
    content = await file.read()
    filename = file.filename or "upload"
    try:
        parsed_mapping = json.loads(mapping)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid column mapping payload.") from exc
    if not isinstance(parsed_mapping, dict):
        raise HTTPException(status_code=400, detail="Invalid column mapping payload.")

    normalized_mapping = {
        str(field_name): (str(source_column) if source_column else None)
        for field_name, source_column in parsed_mapping.items()
    }

    try:
        result = execute_client_import(
            db,
            content=content,
            filename=filename,
            mapping=normalized_mapping,
            created_by_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ClientImportResultResponse(**result)


@router.post("/copilot", response_model=SalesCopilotResponse)
def sales_copilot_route(
    payload: SalesCopilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesCopilotResponse:
    analytics = get_sales_analytics(db, current_user.agency_id)
    try:
        answer = answer_sales_copilot_question(
            db,
            agency_id=current_user.agency_id,
            question=payload.question.strip(),
            analytics=analytics,
        )
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiParseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SalesCopilotResponse(answer=answer)
