from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.brand_logo_storage import upload_agency_logo, upload_agency_signature_image as store_signature_image
from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import User
from app.schemas import (
    AgencyBrandingChromeRead,
    AgencyPublicBrandingRead,
    AgencySettingsLogoUploadResponse,
    AgencySettingsRead,
    AgencySettingsUpdate,
    AgencySignatureImageUploadResponse,
)
from app.services.agency_settings_service import (
    build_portal_branding_payload,
    build_public_branding_payload,
    get_agency_settings_row,
    update_agency_settings,
)

settings_router = APIRouter(prefix="/api/agency", tags=["agency-settings"])
public_router = APIRouter(prefix="/api/public", tags=["public-branding"])

_MAX_LOGO_BYTES = 5 * 1024 * 1024


@settings_router.get("/branding", response_model=AgencyBrandingChromeRead)
def read_agency_branding_chrome(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgencyBrandingChromeRead:
    row = get_agency_settings_row(db, agency_id=current_user.agency_id)
    return AgencyBrandingChromeRead.model_validate(build_portal_branding_payload(row))


@settings_router.get("/settings", response_model=AgencySettingsRead)
def read_agency_settings(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencySettingsRead:
    row = get_agency_settings_row(db, agency_id=current_user.agency_id)
    return AgencySettingsRead.model_validate(row)


@settings_router.put("/settings", response_model=AgencySettingsRead)
def put_agency_settings(
    payload: AgencySettingsUpdate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencySettingsRead:
    row = update_agency_settings(
        db,
        agency_id=current_user.agency_id,
        agency_name=payload.agency_name,
        primary_color=payload.primary_color,
        secondary_color=payload.secondary_color,
        custom_master_tc=payload.custom_master_tc,
        email_signature_block=payload.email_signature_block,
        business_address=payload.business_address,
        business_phone=payload.business_phone,
    )
    return AgencySettingsRead.model_validate(row)


@settings_router.post("/settings/upload-logo", response_model=AgencySettingsLogoUploadResponse)
async def upload_agency_brand_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencySettingsLogoUploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Logo upload must be an image file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Logo file is empty.")
    if len(content) > _MAX_LOGO_BYTES:
        raise HTTPException(status_code=422, detail="Logo file must be 5 MB or smaller.")

    try:
        logo_url = upload_agency_logo(
            current_user.agency_id,
            content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    update_agency_settings(
        db,
        agency_id=current_user.agency_id,
        brand_logo_url=logo_url,
    )
    return AgencySettingsLogoUploadResponse(brand_logo_url=logo_url)


@settings_router.post("/settings/upload-signature-image", response_model=AgencySignatureImageUploadResponse)
async def upload_signature_image_route(
    file: UploadFile = File(...),
    current_user: User = Depends(require_tenant_super_user),
) -> AgencySignatureImageUploadResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Signature image upload must be an image file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="Signature image file is empty.")

    try:
        image_url = store_signature_image(
            current_user.agency_id,
            content,
            filename=file.filename,
            content_type=file.content_type,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AgencySignatureImageUploadResponse(image_url=image_url)


@public_router.get("/agency/{agency_id}/branding", response_model=AgencyPublicBrandingRead)
def read_public_agency_branding(agency_id: str, db: Session = Depends(get_db)) -> AgencyPublicBrandingRead:
    row = get_agency_settings_row(db, agency_id=agency_id)
    return AgencyPublicBrandingRead.model_validate(build_public_branding_payload(row, include_terms=True))
