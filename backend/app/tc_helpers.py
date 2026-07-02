from __future__ import annotations

import hashlib

from app.constants import (
    MASTER_TERMS_BOILERPLATE_TEMPLATE,
    MASTER_TERMS_DEFAULT_BUSINESS_NAME,
    MASTER_TERMS_DEFAULT_GOVERNING_LAW_STATE,
)


def resolve_agency_governing_law_state(
    agency: object | None,
    *,
    governing_law_state: str | None = None,
) -> str:
    if governing_law_state and governing_law_state.strip():
        return governing_law_state.strip()
    if agency is not None:
        state = (getattr(agency, "business_state_or_province", None) or "").strip()
        if state:
            return state
    return MASTER_TERMS_DEFAULT_GOVERNING_LAW_STATE


def resolve_agency_business_name(agency: object | None, *, business_name: str | None = None) -> str:
    if business_name and business_name.strip():
        return business_name.strip()
    if agency is not None:
        name = (getattr(agency, "name", None) or "").strip()
        if name:
            return name
    return MASTER_TERMS_DEFAULT_BUSINESS_NAME


def render_master_terms_text(
    *,
    business_name: str | None = None,
    governing_law_state: str | None = None,
    agency: object | None = None,
) -> str:
    resolved_business_name = resolve_agency_business_name(agency, business_name=business_name)
    resolved_state = resolve_agency_governing_law_state(agency, governing_law_state=governing_law_state)
    return MASTER_TERMS_BOILERPLATE_TEMPLATE.format(
        business_name=resolved_business_name,
        governing_law_state=resolved_state,
    )


def render_master_terms_for_agency(agency: object | None) -> str:
    return render_master_terms_text(agency=agency)


def master_terms_version_hash(
    *,
    business_name: str | None = None,
    governing_law_state: str | None = None,
    agency: object | None = None,
) -> str:
    rendered = render_master_terms_text(
        business_name=business_name,
        governing_law_state=governing_law_state,
        agency=agency,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()
