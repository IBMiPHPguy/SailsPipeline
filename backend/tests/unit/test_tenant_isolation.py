"""Unit tests for central tenant context and ORM-level agency air-gap."""

from datetime import date

import pytest

from app.models import Agency, TravelRequest
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_context import clear_current_agency_id, set_current_agency_id
from app.tenant_roles import SUBSCRIPTION_STATE_ACTIVE

AGENCY_ONE_ID = DEFAULT_AGENCY_ID
AGENCY_TWO_ID = "00000000-0000-4000-8000-000000000002"


@pytest.fixture
def agency_one_travel_request(db) -> TravelRequest:
    clear_current_agency_id()
    request = TravelRequest(
        agency_id=AGENCY_ONE_ID,
        first_name="Jane",
        last_name="Cruiser",
        email="jane@agency-one.example",
        phone="5551234567",
        cruise_lines=["Royal Caribbean International"],
        destination="Caribbean",
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@pytest.fixture
def agency_two(db) -> Agency:
    clear_current_agency_id()
    agency = Agency(
        id=AGENCY_TWO_ID,
        name="Agency Two",
        slug="agency-two",
        organization_handle="agency-two",
        subscription_state=SUBSCRIPTION_STATE_ACTIVE,
        is_active=True,
    )
    db.add(agency)
    db.commit()
    db.refresh(agency)
    return agency


def test_agency_two_context_cannot_read_agency_one_travel_request(
    db,
    agency_two,
    agency_one_travel_request,
):
    set_current_agency_id(AGENCY_TWO_ID)

    leaked = db.query(TravelRequest).filter(TravelRequest.id == agency_one_travel_request.id).first()

    assert leaked is None


def test_agency_one_context_can_read_own_travel_request(db, agency_one_travel_request):
    set_current_agency_id(AGENCY_ONE_ID)

    found = db.query(TravelRequest).filter(TravelRequest.id == agency_one_travel_request.id).first()

    assert found is not None
    assert found.id == agency_one_travel_request.id
    assert found.agency_id == AGENCY_ONE_ID


def test_fail_closed_blocks_tenant_query_without_agency_id_on_crm_path(db, agency_one_travel_request):
    from app.tenant_context import TenantContextRequiredError, set_tenant_scoping_required

    clear_current_agency_id()
    set_tenant_scoping_required(True)

    with pytest.raises(TenantContextRequiredError):
        db.query(TravelRequest).filter(TravelRequest.id == agency_one_travel_request.id).first()
