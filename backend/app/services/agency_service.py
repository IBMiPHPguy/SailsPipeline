from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Agency, Passenger, TravelRequest, User
from app.tenant_constants import (
    DEFAULT_AGENCY_ID,
    DEFAULT_AGENCY_NAME,
    DEFAULT_AGENCY_ORGANIZATION_HANDLE,
    DEFAULT_AGENCY_SLUG,
)
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE, USER_ROLE_TENANT_SUPER_USER

T = TypeVar("T")

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


def ensure_default_agency(db: Session) -> Agency:
    agency = db.get(Agency, DEFAULT_AGENCY_ID)
    if agency is not None:
        if not (agency.organization_handle or "").strip():
            agency.organization_handle = DEFAULT_AGENCY_ORGANIZATION_HANDLE
        elif (
            agency.organization_handle == DEFAULT_AGENCY_ORGANIZATION_HANDLE
            and agency.slug not in ("", DEFAULT_AGENCY_SLUG)
            and agency.slug != agency.organization_handle
        ):
            # Recover from an earlier startup bug that reset organization_handle but left slug intact.
            agency.organization_handle = agency.slug
        if not (agency.subscription_state or "").strip():
            agency.subscription_state = SUBSCRIPTION_STATE_ACTIVE
        return agency

    agency = Agency(
        id=DEFAULT_AGENCY_ID,
        name=DEFAULT_AGENCY_NAME,
        slug=DEFAULT_AGENCY_SLUG,
        organization_handle=DEFAULT_AGENCY_ORGANIZATION_HANDLE,
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    db.add(agency)
    db.flush()
    return agency


def assert_same_agency(*, entity_agency_id: str, expected_agency_id: str) -> None:
    if entity_agency_id != expected_agency_id:
        raise NOT_FOUND


def get_travel_request_for_agency(db: Session, request_id: int, agency_id: str) -> TravelRequest:
    request = db.get(TravelRequest, request_id)
    if request is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=request.agency_id, expected_agency_id=agency_id)
    return request


def get_travel_request_for_user(
    db: Session,
    request_id: int,
    user: User,
    *,
    require_manage: bool = False,
) -> TravelRequest:
    """Agency-scoped request load with agent capability checks."""
    from app.services.agent_capability_service import (
        assert_can_manage_request,
        assert_can_view_request,
        get_capabilities_for_user,
    )

    if user.agency_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership required.")
    request = get_travel_request_for_agency(db, request_id, user.agency_id)
    caps = get_capabilities_for_user(db, user)
    if require_manage:
        assert_can_manage_request(user, request, caps)
    else:
        assert_can_view_request(user, request, caps)
    return request


def get_passenger_for_agency(db: Session, passenger_id: int, agency_id: str) -> Passenger:
    passenger = db.get(Passenger, passenger_id)
    if passenger is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=passenger.agency_id, expected_agency_id=agency_id)
    return passenger


def get_marketing_campaign_for_agency(db: Session, campaign_id: str, agency_id: str):
    from app.models import MarketingCampaign

    campaign = db.get(MarketingCampaign, campaign_id)
    if campaign is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=campaign.agency_id, expected_agency_id=agency_id)
    return campaign


def assert_child_belongs_to_request(
    *,
    child_agency_id: str,
    child_travel_request_id: int,
    request_id: int,
    agency_id: str,
) -> None:
    if child_travel_request_id != request_id:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=child_agency_id, expected_agency_id=agency_id)


def require_record_for_agency(
    record: T | None,
    *,
    agency_id: str,
    agency_id_attr: str = "agency_id",
) -> T:
    if record is None:
        raise NOT_FOUND
    record_agency_id = getattr(record, agency_id_attr, None)
    if record_agency_id is None:
        raise NOT_FOUND
    assert_same_agency(entity_agency_id=record_agency_id, expected_agency_id=agency_id)
    return record


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def get_agency_profile(db: Session, *, agency_id: str) -> Agency:
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise NOT_FOUND
    return agency


def update_agency_business_address(
    db: Session,
    *,
    agency_id: str,
    business_address_line_1: str | None = None,
    business_address_line_2: str | None = None,
    business_city: str | None = None,
    business_state_or_province: str | None = None,
    business_postal_code: str | None = None,
    business_country: str | None = None,
) -> Agency:
    agency = get_agency_profile(db, agency_id=agency_id)
    agency.business_address_line_1 = _normalize_optional_text(business_address_line_1)
    agency.business_address_line_2 = _normalize_optional_text(business_address_line_2)
    agency.business_city = _normalize_optional_text(business_city)
    agency.business_state_or_province = _normalize_optional_text(business_state_or_province)
    agency.business_postal_code = _normalize_optional_text(business_postal_code)
    agency.business_country = _normalize_optional_text(business_country)
    db.commit()
    db.refresh(agency)
    return agency
