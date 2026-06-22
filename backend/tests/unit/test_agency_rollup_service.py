from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.constants import (
    PRIMARY_CLOSE_REASON,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
)
from app.models import AgencyDashboardRollup, AgencyReportMetadataCache, Passenger, ProposedCruise, TravelRequest, User
from app.security import hash_password
from app.services.agency_rollup_service import (
    refresh_agency_dashboard_rollups,
    refresh_agency_report_metadata_cache,
    refresh_agency_rollups,
    rollup_refresh_triggers_on_cruise_status,
    schedule_agency_rollup_refresh,
)
from app.services.dashboard_service import get_dashboard
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_roles import USER_ROLE_TENANT_AGENT


@pytest.mark.unit
def test_rollup_refresh_triggers_on_cruise_status():
    assert rollup_refresh_triggers_on_cruise_status("Accepted") is True
    assert rollup_refresh_triggers_on_cruise_status("Deposited") is True
    assert rollup_refresh_triggers_on_cruise_status("Rejected") is True
    assert rollup_refresh_triggers_on_cruise_status("Proposed") is False


@pytest.mark.unit
def test_refresh_agency_dashboard_rollups_persists_counts(db, test_user):
    open_request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Open",
        last_name="Lead",
        email="open@example.com",
        phone="5551112222",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    closed_request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Closed",
        last_name="Lead",
        email="closed@example.com",
        phone="5553334444",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Alaska",
        destination_details=None,
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason=PRIMARY_CLOSE_REASON,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add_all([open_request, closed_request])
    db.flush()

    pending_cruise = ProposedCruise(
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=open_request.id,
        departure_date=date(2026, 7, 1),
        cruise_line="Royal Caribbean International",
        ship="Wonder",
        number_of_nights=7,
        itinerary_name="Eastern Caribbean",
        room_category="Balcony",
        room_number="1234",
        passengers_in_room=2,
        deposit_amount=500,
        deposit_due_date=date(2026, 5, 1),
        final_payment_due_date=date(2026, 6, 1),
        cost=2500,
        includes={"gratuities": False, "wifi": False, "beverages": False, "insurance": False},
        status=PROPOSED_CRUISE_STATUS_PROPOSED,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    deposited_cruise = ProposedCruise(
        agency_id=DEFAULT_AGENCY_ID,
        travel_request_id=closed_request.id,
        departure_date=date(2026, 8, 1),
        cruise_line="Royal Caribbean International",
        ship="Oasis",
        number_of_nights=7,
        itinerary_name="Alaska",
        room_category="Balcony",
        room_number="5678",
        passengers_in_room=2,
        deposit_amount=600,
        deposit_due_date=date(2026, 6, 1),
        final_payment_due_date=date(2026, 7, 1),
        cost=4000,
        cabin_rooms=[{"commission": 400}],
        includes={"gratuities": False, "wifi": False, "beverages": False, "insurance": False},
        status=PROPOSED_CRUISE_STATUS_DEPOSITED,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add_all([pending_cruise, deposited_cruise])
    db.commit()

    rollup = refresh_agency_dashboard_rollups(db, DEFAULT_AGENCY_ID)

    assert rollup.open_leads_count == 1
    assert rollup.proposals_pending_count == 1
    assert rollup.completed_bookings_count == 1
    assert float(rollup.total_volume_booked) == 4000.0
    assert float(rollup.total_commission_booked) == 400.0
    assert rollup.closed_count == 1
    assert rollup.purchased_closed_count == 1
    assert rollup.last_refreshed_at is not None


@pytest.mark.unit
def test_refresh_agency_dashboard_rollups_sums_back_to_back_booked_cruises(db, test_user):
    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Back",
        last_name="ToBack",
        email="b2b@example.com",
        phone="5551113333",
        cruise_lines=["Royal Caribbean International", "Celebrity Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        created_by_id=test_user.id,
        updated_by_id=test_user.id,
    )
    db.add(request)
    db.flush()

    db.add_all(
        [
            ProposedCruise(
                agency_id=DEFAULT_AGENCY_ID,
                travel_request_id=request.id,
                departure_date=date(2026, 7, 1),
                cruise_line="Royal Caribbean International",
                ship="Wonder",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="1234",
                passengers_in_room=2,
                deposit_amount=500,
                deposit_due_date=date(2026, 5, 1),
                final_payment_due_date=date(2026, 6, 1),
                cost=5000,
                cabin_rooms=[{"commission": 500}],
                includes={"gratuities": False, "wifi": False, "beverages": False, "insurance": False},
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by_id=test_user.id,
                updated_by_id=test_user.id,
            ),
            ProposedCruise(
                agency_id=DEFAULT_AGENCY_ID,
                travel_request_id=request.id,
                departure_date=date(2026, 8, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="5678",
                passengers_in_room=2,
                deposit_amount=600,
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 7, 1),
                cost=4000,
                cabin_rooms=[{"commission": 400}],
                includes={"gratuities": False, "wifi": False, "beverages": False, "insurance": False},
                status=PROPOSED_CRUISE_STATUS_DEPOSITED,
                created_by_id=test_user.id,
                updated_by_id=test_user.id,
            ),
        ]
    )
    db.commit()

    rollup = refresh_agency_dashboard_rollups(db, DEFAULT_AGENCY_ID)

    assert rollup.completed_bookings_count == 2
    assert float(rollup.total_volume_booked) == 9000.0
    assert float(rollup.total_commission_booked) == 900.0
    assert float(rollup.total_pipeline_value) == 9000.0


@pytest.mark.unit
def test_refresh_agency_report_metadata_cache_stores_active_advisors_and_states(db, test_user):
    agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="rollupagent",
        email="rollupagent@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
        is_active=True,
    )
    inactive_agent = User(
        agency_id=DEFAULT_AGENCY_ID,
        username="inactiveagent",
        email="inactiveagent@example.com",
        password_hash=hash_password("ValidPass1!"),
        role=USER_ROLE_TENANT_AGENT,
        is_active=False,
    )
    db.add_all([agent, inactive_agent])
    db.flush()

    request = TravelRequest(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="Meta",
        last_name="Client",
        email="meta@example.com",
        phone="5559998888",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 9, 1),
        return_date=date(2026, 9, 8),
        cabin_types=["Balcony"],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        created_by_id=agent.id,
        updated_by_id=agent.id,
    )
    db.add(request)
    db.flush()

    passenger = Passenger(
        agency_id=DEFAULT_AGENCY_ID,
        first_name="State",
        last_name="Resident",
        email="state@example.com",
        phone="5557776666",
        state_or_province="FL",
        is_active=True,
        created_by_id=test_user.id,
    )
    db.add(passenger)
    db.commit()

    cache = refresh_agency_report_metadata_cache(db, DEFAULT_AGENCY_ID)

    assert "rollupagent" in cache.active_advisor_names
    assert "inactiveagent" not in cache.active_advisor_names
    assert "FL" in cache.active_residence_states


@pytest.mark.unit
def test_get_dashboard_reads_persisted_rollups(db, test_user):
    rollup = AgencyDashboardRollup(
        agency_id=DEFAULT_AGENCY_ID,
        open_leads_count=4,
        proposals_pending_count=2,
        completed_bookings_count=3,
        total_volume_booked=Decimal("12000.00"),
        total_commission_booked=Decimal("900.00"),
        stale_count=1,
        closed_count=5,
        purchased_closed_count=3,
        total_pipeline_value=Decimal("4500.00"),
        last_refreshed_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(rollup)
    db.commit()

    dashboard = get_dashboard(db, DEFAULT_AGENCY_ID)

    assert dashboard.open_count == 4
    assert dashboard.stale_count == 1
    assert dashboard.closed_count == 5
    assert dashboard.purchased_closed_count == 3
    assert dashboard.other_closed_count == 2
    assert dashboard.successful_sales_close_rate == 60.0
    assert dashboard.total_pipeline_value == 4500.0


@pytest.mark.unit
def test_schedule_and_refresh_all_agencies(db, test_user):
    schedule_agency_rollup_refresh(DEFAULT_AGENCY_ID)
    dashboard, metadata = refresh_agency_rollups(db, DEFAULT_AGENCY_ID)
    assert isinstance(dashboard, AgencyDashboardRollup)
    assert isinstance(metadata, AgencyReportMetadataCache)
    assert refresh_agency_rollups(db, DEFAULT_AGENCY_ID)[0].agency_id == DEFAULT_AGENCY_ID
