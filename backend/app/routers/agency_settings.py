from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.brand_logo_storage import (
    purge_stale_local_brand_logo,
    upload_agency_logo,
    upload_agency_signature_image as store_signature_image,
)
from app.database import get_db
from app.deps import get_current_user, require_tenant_super_user
from app.models import Agency, User
from app.schemas import (
    AgencyAiSettingsRead,
    AgencyAiSettingsUpdate,
    AgencyAiStatusRead,
    AgencyBrandingChromeRead,
    AgentConfigurablePermissionsRead,
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
from app.services.agent_capability_service import get_configurable_permissions_for_agency
from app.services.gemini_config_service import (
    agency_has_gemini_api_key,
    clear_agency_gemini_api_key,
    is_gemini_configured,
    save_agency_gemini_api_key,
    uses_tenant_gemini_api_key,
)
from app.tenant_roles import USER_ROLE_TENANT_SUPER_USER

settings_router = APIRouter(prefix="/api/agency", tags=["agency-settings"])
public_router = APIRouter(prefix="/api/public", tags=["public-branding"])

_MAX_LOGO_BYTES = 5 * 1024 * 1024


def _settings_to_read(db: Session, row, *, agency_id: str) -> AgencySettingsRead:
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found.")
    permissions = get_configurable_permissions_for_agency(db, agency_id=agency_id)
    return AgencySettingsRead(
        agency_id=row.agency_id,
        organization_handle=agency.organization_handle,
        agency_name=row.agency_name,
        brand_logo_url=row.brand_logo_url,
        primary_color=row.primary_color,
        secondary_color=row.secondary_color,
        custom_master_tc=row.custom_master_tc,
        email_signature_block=row.email_signature_block,
        business_address=row.business_address,
        business_phone=row.business_phone,
        agent_permissions=AgentConfigurablePermissionsRead.model_validate(permissions.model_dump()),
    )


@settings_router.get("/branding", response_model=AgencyBrandingChromeRead)
def read_agency_branding_chrome(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgencyBrandingChromeRead:
    row = get_agency_settings_row(db, agency_id=current_user.agency_id)
    return AgencyBrandingChromeRead.model_validate(build_portal_branding_payload(row))


@settings_router.get("/ai-status", response_model=AgencyAiStatusRead)
def read_agency_ai_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgencyAiStatusRead:
    return AgencyAiStatusRead(
        configured=is_gemini_configured(db, agency_id=current_user.agency_id),
        can_manage=current_user.role == USER_ROLE_TENANT_SUPER_USER,
        uses_tenant_key=uses_tenant_gemini_api_key(),
    )


@settings_router.get("/ai-settings", response_model=AgencyAiSettingsRead)
def read_agency_ai_settings(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyAiSettingsRead:
    row = get_agency_settings_row(db, agency_id=current_user.agency_id)
    configured = agency_has_gemini_api_key(row) if uses_tenant_gemini_api_key() else is_gemini_configured(
        db, agency_id=current_user.agency_id
    )
    return AgencyAiSettingsRead(configured=configured)


@settings_router.put("/ai-settings", response_model=AgencyAiSettingsRead)
def put_agency_ai_settings(
    payload: AgencyAiSettingsUpdate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyAiSettingsRead:
    if not uses_tenant_gemini_api_key():
        raise HTTPException(
            status_code=400,
            detail="Agency AI keys are only managed in production. Local development uses GEMINI_API_KEY.",
        )
    try:
        row = save_agency_gemini_api_key(
            db,
            agency_id=current_user.agency_id,
            api_key=payload.gemini_api_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AgencyAiSettingsRead(configured=agency_has_gemini_api_key(row))


@settings_router.delete("/ai-settings", response_model=AgencyAiSettingsRead)
def delete_agency_ai_settings(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencyAiSettingsRead:
    if not uses_tenant_gemini_api_key():
        raise HTTPException(
            status_code=400,
            detail="Agency AI keys are only managed in production. Local development uses GEMINI_API_KEY.",
        )
    clear_agency_gemini_api_key(db, agency_id=current_user.agency_id)
    return AgencyAiSettingsRead(configured=False)


@settings_router.get("/settings", response_model=AgencySettingsRead)
def read_agency_settings(
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencySettingsRead:
    row = get_agency_settings_row(db, agency_id=current_user.agency_id)
    return _settings_to_read(db, row, agency_id=current_user.agency_id)


@settings_router.put("/settings", response_model=AgencySettingsRead)
def put_agency_settings(
    payload: AgencySettingsUpdate,
    current_user: User = Depends(require_tenant_super_user),
    db: Session = Depends(get_db),
) -> AgencySettingsRead:
    permissions_payload = None
    if payload.agent_permissions is not None:
        permissions_payload = payload.agent_permissions.model_dump()
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
        agent_permissions=permissions_payload,
    )
    return _settings_to_read(db, row, agency_id=current_user.agency_id)


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

    current_settings = get_agency_settings_row(db, agency_id=current_user.agency_id)
    purge_stale_local_brand_logo(current_settings.brand_logo_url)

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
