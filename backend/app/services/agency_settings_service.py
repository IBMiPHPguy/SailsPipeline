from __future__ import annotations

import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.brand_logo_storage import externalize_inline_signature_images
from app.constants import MASTER_TERMS_DEFAULT_BUSINESS_NAME
from app.models import Agency, AgencySettings
from app.tc_helpers import render_master_terms_text
from app.tenant_constants import DEFAULT_AGENCY_ID

HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
DEFAULT_PRIMARY_COLOR = "#0d5c75"
DEFAULT_SECONDARY_COLOR = "#17a2b8"

NOT_FOUND = HTTPException(status_code=404, detail="Agency settings not found.")


def compose_business_address_from_agency(agency: Agency | None) -> str | None:
    if agency is None:
        return None
    parts = [
        (agency.business_address_line_1 or "").strip(),
        (agency.business_address_line_2 or "").strip(),
        (agency.business_city or "").strip(),
        (agency.business_state_or_province or "").strip(),
        (agency.business_postal_code or "").strip(),
        (agency.business_country or "").strip(),
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or None


def default_master_terms_seed_text() -> str:
    return render_master_terms_text(
        business_name=MASTER_TERMS_DEFAULT_BUSINESS_NAME,
        governing_law_state="Utah",
    )


def seed_agency_settings_for_tenant(
    db: Session,
    *,
    agency_id: str,
    agency_name: str,
) -> AgencySettings:
    """Provision default branding, colors, and master T&C boilerplate for a new tenant."""
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise NOT_FOUND

    normalized_name = agency_name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Agency name is required.")

    seed_terms = render_master_terms_text(
        business_name=normalized_name,
        governing_law_state="Utah",
        agency=agency,
    )

    existing = db.get(AgencySettings, agency_id)
    if existing is None:
        row = AgencySettings(
            agency_id=agency_id,
            agency_name=normalized_name,
            primary_color=DEFAULT_PRIMARY_COLOR,
            secondary_color=DEFAULT_SECONDARY_COLOR,
            custom_master_tc=seed_terms,
            business_address=compose_business_address_from_agency(agency),
        )
        db.add(row)
        db.flush()
        return row

    if not (existing.custom_master_tc or "").strip():
        existing.custom_master_tc = seed_terms
    if not (existing.agency_name or "").strip():
        existing.agency_name = normalized_name
    if not (existing.business_address or "").strip():
        existing.business_address = compose_business_address_from_agency(agency)
    db.flush()
    return existing


def seed_default_agency_settings(db: Session) -> None:
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    if agency is None:
        return

    existing = db.get(AgencySettings, DEFAULT_AGENCY_ID)
    seed_terms = default_master_terms_seed_text()
    if existing is None:
        db.add(
            AgencySettings(
                agency_id=DEFAULT_AGENCY_ID,
                agency_name=MASTER_TERMS_DEFAULT_BUSINESS_NAME,
                primary_color=DEFAULT_PRIMARY_COLOR,
                secondary_color=DEFAULT_SECONDARY_COLOR,
                custom_master_tc=seed_terms,
                business_address=compose_business_address_from_agency(agency),
            )
        )
    else:
        if not (existing.custom_master_tc or "").strip():
            existing.custom_master_tc = seed_terms
        if existing.agency_name.strip() in {"", "Default Agency"}:
            existing.agency_name = MASTER_TERMS_DEFAULT_BUSINESS_NAME
        if not (existing.business_address or "").strip():
            existing.business_address = compose_business_address_from_agency(agency)
    db.commit()


def get_agency_settings_row(db: Session, *, agency_id: str) -> AgencySettings:
    row = db.get(AgencySettings, agency_id)
    if row is not None:
        return row

    agency = db.get(Agency, agency_id)
    if agency is None:
        raise NOT_FOUND

    row = AgencySettings(
        agency_id=agency_id,
        agency_name=agency.name,
        primary_color=DEFAULT_PRIMARY_COLOR,
        secondary_color=DEFAULT_SECONDARY_COLOR,
        business_address=compose_business_address_from_agency(agency),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def validate_hex_color(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not HEX_COLOR_PATTERN.fullmatch(normalized):
        raise HTTPException(status_code=422, detail=f"{field_name} must be a hex color like #0d5c75.")
    return normalized.lower()


def update_agency_settings(
    db: Session,
    *,
    agency_id: str,
    agency_name: str | None = None,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    custom_master_tc: str | None = None,
    email_signature_block: str | None = None,
    business_address: str | None = None,
    business_phone: str | None = None,
    brand_logo_url: str | None = None,
    agent_permissions: dict | None = None,
) -> AgencySettings:
    row = get_agency_settings_row(db, agency_id=agency_id)

    if agency_name is not None:
        row.agency_name = agency_name.strip()
        agency = db.get(Agency, agency_id)
        if agency is not None and agency.name != row.agency_name:
            agency.name = row.agency_name
    if primary_color is not None:
        row.primary_color = validate_hex_color(primary_color, field_name="primary_color")
    if secondary_color is not None:
        row.secondary_color = validate_hex_color(secondary_color, field_name="secondary_color")
    if custom_master_tc is not None:
        row.custom_master_tc = custom_master_tc.strip() or None
    if email_signature_block is not None:
        normalized_signature = email_signature_block.strip() or None
        if normalized_signature:
            normalized_signature = externalize_inline_signature_images(agency_id, normalized_signature)
        row.email_signature_block = normalized_signature
    if business_address is not None:
        row.business_address = business_address.strip() or None
    if business_phone is not None:
        row.business_phone = business_phone.strip() or None
    if brand_logo_url is not None:
        row.brand_logo_url = brand_logo_url.strip() or None
    if agent_permissions is not None:
        from app.agent_capabilities import validate_configurable_permissions_payload

        try:
            normalized = validate_configurable_permissions_payload(agent_permissions)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        row.agent_permissions = normalized.model_dump()

    db.commit()
    db.refresh(row)
    return row


def resolve_terms_text(db: Session, *, agency_id: str, agency: Agency | None = None) -> str:
    row = get_agency_settings_row(db, agency_id=agency_id)
    custom = (row.custom_master_tc or "").strip()
    if custom:
        return custom
    return render_master_terms_text(agency=agency or db.get(Agency, agency_id))


def build_public_branding_payload(row: AgencySettings, *, include_terms: bool = False) -> dict:
    payload = {
        "agency_id": row.agency_id,
        "agency_name": row.agency_name,
        "brand_logo_url": row.brand_logo_url,
        "primary_color": row.primary_color,
        "secondary_color": row.secondary_color,
        "business_address": row.business_address,
        "business_phone": row.business_phone,
    }
    if include_terms:
        payload["custom_master_tc"] = row.custom_master_tc
    return payload


def build_portal_branding_payload(row: AgencySettings) -> dict:
    return {
        "agency_name": row.agency_name,
        "brand_logo_url": row.brand_logo_url,
        "primary_color": row.primary_color,
        "secondary_color": row.secondary_color,
        "business_address": row.business_address,
        "business_phone": row.business_phone,
    }
