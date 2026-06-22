from datetime import date

from app.constants import (
    PROPOSED_CRUISE_REJECTION_REASON_PRICE,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_PROPOSED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
)
from app.models import Passenger, ProposedCruise, TravelRequest, User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.services.reports_service import (
    ReportQueryFilters,
    get_advisor_scorecard_page,
    get_funnel_leak_page,
    get_passenger_demographics_page,
    get_report_meta,
    get_sales_manifest_page,
    get_supplier_ledger_page,
)


def _create_user(db, *, username: str) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()
    return user


def _create_request(db, *, user: User, cruise_line: str = "Royal Caribbean International") -> TravelRequest:
    request = TravelRequest(
        first_name="Jamie",
        last_name="Cruise",
        email="jamie@example.com",
        phone="555-0100",
        cruise_lines=[cruise_line],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details=None,
        departure_date=date(2026, 3, 15),
        return_date=date(2026, 3, 22),
        cabin_types=["Balcony"],
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        created_by_id=user.id,
        updated_by_id=user.id,
    )
    db.add(request)
    db.flush()
    return request


def test_get_report_meta_groups_workflow_tasks_in_sequence(db):
    meta = get_report_meta(db, DEFAULT_AGENCY_ID)
    assert len(meta.workflow_task_groups) == 3

    research = meta.workflow_task_groups[0]
    assert research.workflow_name == "Research"
    assert [task.value for task in research.tasks] == [
        "task:research_cruise_options",
        "task:upload_research_document",
        "task:create_proposed_cruises",
        "task:draft_research_communication",
    ]

    communicate = next(group for group in meta.workflow_task_groups if group.workflow_type == "communicate_research")
    assert communicate.tasks[0].value == "task:send_research_communication"
    assert all(not task.value.startswith("workflow:") for group in meta.workflow_task_groups for task in group.tasks)


def test_sales_manifest_page_filters_by_supplier(db):
    user = _create_user(db, username="report-agent")
    royal = _create_request(db, user=user, cruise_line="Royal Caribbean International")
    celebrity = _create_request(db, user=user, cruise_line="Celebrity Cruises")
    db.add(
        ProposedCruise(
            travel_request_id=royal.id,
            departure_date=date(2026, 3, 15),
            cruise_line="Royal Caribbean International",
            ship="Icon of the Seas",
            number_of_nights=7,
            itinerary_name="Western Caribbean",
            room_category="Balcony",
            room_number="TBD",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 1, 15),
            final_payment_due_date=date(2026, 2, 15),
            cost=4200,
            cabin_rooms=[{"commission": 420}],
            status=PROPOSED_CRUISE_STATUS_PROPOSED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.add(
        ProposedCruise(
            travel_request_id=celebrity.id,
            departure_date=date(2026, 4, 10),
            cruise_line="Celebrity Cruises",
            ship="Ascent",
            number_of_nights=7,
            itinerary_name="Eastern Caribbean",
            room_category="Balcony",
            room_number="TBD",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 2, 1),
            final_payment_due_date=date(2026, 3, 1),
            cost=5100,
            cabin_rooms=[{"commission": 510}],
            status=PROPOSED_CRUISE_STATUS_PROPOSED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.commit()

    page = get_sales_manifest_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,cruise_line="Royal Caribbean International"))
    assert page.total == 1
    assert page.items[0].request_id == royal.id
    assert page.items[0].cruise_line == "Royal Caribbean International"
    assert page.items[0].estimated_gross_booking_total == 4200.0
    assert page.items[0].projected_commission_target == 420.0


def test_sales_manifest_pipeline_status_reflects_request_open_or_closed(db):
    user = _create_user(db, username="status-agent")
    open_request = _create_request(db, user=user)
    closed_request = _create_request(db, user=user, cruise_line="Celebrity Cruises")
    closed_request.status = REQUEST_STATUS_CLOSED
    db.commit()

    page = get_sales_manifest_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,))
    statuses = {row.request_id: row.pipeline_status for row in page.items}
    assert statuses[open_request.id] == "Open"
    assert statuses[closed_request.id] == "Closed"

    open_only = get_sales_manifest_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,pipeline_status="open"))
    assert open_only.total == 1
    assert open_only.items[0].request_id == open_request.id


def test_supplier_ledger_page_aggregates_deposited_volume(db):
    user = _create_user(db, username="ledger-agent")
    request = _create_request(db, user=user)
    db.add(
        ProposedCruise(
            travel_request_id=request.id,
            departure_date=date(2026, 3, 15),
            cruise_line="Royal Caribbean International",
            ship="Icon of the Seas",
            number_of_nights=7,
            itinerary_name="Western Caribbean",
            room_category="Balcony",
            room_number="1234",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 1, 15),
            final_payment_due_date=date(2026, 2, 15),
            cost=4000,
            cabin_rooms=[{"commission": 400}],
            status=PROPOSED_CRUISE_STATUS_DEPOSITED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.commit()

    page = get_supplier_ledger_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,))
    assert page.total == 1
    row = page.items[0]
    assert row.cruise_line == "Royal Caribbean International"
    assert row.active_booking_count == 1
    assert row.total_volume == 4000.0
    assert row.total_commission_booked == 400.0
    assert row.average_commission_rate_percent == 10.0


def test_supplier_ledger_page_includes_accepted_and_deposited_cruises(db):
    user = _create_user(db, username="ledger-status-agent")
    open_request = _create_request(db, user=user)
    closed_request = _create_request(db, user=user, cruise_line="Celebrity Cruises")
    closed_request.status = REQUEST_STATUS_CLOSED
    db.add(
        ProposedCruise(
            travel_request_id=open_request.id,
            departure_date=date(2026, 3, 15),
            cruise_line="Royal Caribbean International",
            ship="Icon of the Seas",
            number_of_nights=7,
            itinerary_name="Western Caribbean",
            room_category="Balcony",
            room_number="1234",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 1, 15),
            final_payment_due_date=date(2026, 2, 15),
            cost=4000,
            cabin_rooms=[{"commission": 400}],
            status=PROPOSED_CRUISE_STATUS_ACCEPTED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.add(
        ProposedCruise(
            travel_request_id=closed_request.id,
            departure_date=date(2026, 4, 10),
            cruise_line="Celebrity Cruises",
            ship="Ascent",
            number_of_nights=7,
            itinerary_name="Eastern Caribbean",
            room_category="Balcony",
            room_number="5678",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 2, 1),
            final_payment_due_date=date(2026, 3, 1),
            cost=5100,
            cabin_rooms=[{"commission": 510}],
            status=PROPOSED_CRUISE_STATUS_DEPOSITED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.commit()

    page = get_supplier_ledger_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,))
    assert page.total == 2
    lines = {row.cruise_line: row for row in page.items}
    assert lines["Royal Caribbean International"].active_booking_count == 1
    assert lines["Royal Caribbean International"].total_volume == 4000.0
    assert lines["Celebrity Cruises"].active_booking_count == 1
    assert lines["Celebrity Cruises"].total_volume == 5100.0


def test_supplier_ledger_page_splits_side_by_side_bookings_on_one_request(db):
    user = _create_user(db, username="ledger-b2b-agent")
    request = _create_request(db, user=user)
    db.add_all(
        [
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 3, 15),
                cruise_line="Royal Caribbean International",
                ship="Icon of the Seas",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="1234",
                passengers_in_room=2,
                deposit_amount=500,
                deposit_due_date=date(2026, 1, 15),
                final_payment_due_date=date(2026, 2, 15),
                cost=5000,
                cabin_rooms=[{"commission": 500}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 4, 10),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="5678",
                passengers_in_room=2,
                deposit_amount=500,
                deposit_due_date=date(2026, 2, 1),
                final_payment_due_date=date(2026, 3, 1),
                cost=4000,
                cabin_rooms=[{"commission": 400}],
                status=PROPOSED_CRUISE_STATUS_DEPOSITED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
        ]
    )
    db.commit()

    page = get_supplier_ledger_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,))
    assert page.total == 2
    lines = {row.cruise_line: row for row in page.items}
    assert lines["Royal Caribbean International"].active_booking_count == 1
    assert lines["Royal Caribbean International"].total_volume == 5000.0
    assert lines["Celebrity Cruises"].active_booking_count == 1
    assert lines["Celebrity Cruises"].total_volume == 4000.0


def test_sales_manifest_page_sums_back_to_back_booked_cruises(db):
    user = _create_user(db, username="manifest-b2b-agent")
    request = _create_request(db, user=user)
    db.add_all(
        [
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 3, 15),
                cruise_line="Royal Caribbean International",
                ship="Icon of the Seas",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="1234",
                passengers_in_room=2,
                deposit_amount=500,
                deposit_due_date=date(2026, 1, 15),
                final_payment_due_date=date(2026, 2, 15),
                cost=5000,
                cabin_rooms=[{"commission": 500}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 4, 10),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="5678",
                passengers_in_room=2,
                deposit_amount=500,
                deposit_due_date=date(2026, 2, 1),
                final_payment_due_date=date(2026, 3, 1),
                cost=4000,
                cabin_rooms=[{"commission": 400}],
                status=PROPOSED_CRUISE_STATUS_DEPOSITED,
                created_by_id=user.id,
                updated_by_id=user.id,
            ),
        ]
    )
    db.commit()

    page = get_sales_manifest_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,))
    row = next(item for item in page.items if item.request_id == request.id)
    assert row.estimated_gross_booking_total == 9000.0
    assert row.projected_commission_target == 900.0


def test_funnel_leak_page_includes_rejected_quotes(db):
    user = _create_user(db, username="funnel-agent")
    request = _create_request(db, user=user)
    db.add(
        ProposedCruise(
            travel_request_id=request.id,
            departure_date=date(2026, 3, 15),
            cruise_line="Royal Caribbean International",
            ship="Icon of the Seas",
            number_of_nights=7,
            itinerary_name="Western Caribbean",
            room_category="Balcony",
            room_number="TBD",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 1, 15),
            final_payment_due_date=date(2026, 2, 15),
            cost=3900,
            cabin_rooms=[{"commission": 390}],
            status=PROPOSED_CRUISE_STATUS_REJECTED,
            rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.commit()

    page = get_funnel_leak_page(
        db,
        ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,
            rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
            cruise_line="Royal Caribbean International",
        ),
    )
    matching = [row for row in page.items if row.request_id == request.id]
    assert len(matching) == 1
    row = matching[0]
    assert row.request_id == request.id
    assert row.loss_segment == "rejected_quote"
    assert row.primary_rejection_reason == PROPOSED_CRUISE_REJECTION_REASON_PRICE
    assert row.estimated_value_lost == 3900.0

    filtered = get_funnel_leak_page(
        db,
        ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE),
    )
    assert any(item.request_id == request.id for item in filtered.items)

    empty = get_funnel_leak_page(
        db,
        ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,rejection_reason="Dates", cruise_line="Royal Caribbean International"),
    )
    assert not any(item.request_id == request.id for item in empty.items)


def test_funnel_leak_page_includes_closed_without_booking(db):
    user = _create_user(db, username="closed-lost-agent")
    request = _create_request(db, user=user)
    request.status = REQUEST_STATUS_CLOSED
    request.close_reason = "Client went elsewhere"
    db.commit()

    page = get_funnel_leak_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,loss_segment="closed_lost"))
    matching = [row for row in page.items if row.request_id == request.id]
    assert len(matching) == 1
    assert matching[0].loss_segment == "closed_lost"


def test_advisor_scorecard_page_tracks_productivity_metrics(db):
    user = _create_user(db, username="scorecard-agent")
    open_request = _create_request(db, user=user)
    closed_request = _create_request(db, user=user, cruise_line="Celebrity Cruises")
    closed_request.status = REQUEST_STATUS_CLOSED
    db.add(
        ProposedCruise(
            travel_request_id=open_request.id,
            departure_date=date(2026, 3, 15),
            cruise_line="Royal Caribbean International",
            ship="Icon of the Seas",
            number_of_nights=7,
            itinerary_name="Western Caribbean",
            room_category="Balcony",
            room_number="TBD",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 1, 15),
            final_payment_due_date=date(2026, 2, 15),
            cost=4200,
            cabin_rooms=[{"commission": 420}],
            status=PROPOSED_CRUISE_STATUS_PROPOSED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.add(
        ProposedCruise(
            travel_request_id=closed_request.id,
            departure_date=date(2026, 4, 10),
            cruise_line="Celebrity Cruises",
            ship="Ascent",
            number_of_nights=7,
            itinerary_name="Eastern Caribbean",
            room_category="Balcony",
            room_number="1234",
            passengers_in_room=2,
            deposit_amount=500,
            deposit_due_date=date(2026, 2, 1),
            final_payment_due_date=date(2026, 3, 1),
            cost=5100,
            cabin_rooms=[{"commission": 510}],
            status=PROPOSED_CRUISE_STATUS_DEPOSITED,
            created_by_id=user.id,
            updated_by_id=user.id,
        )
    )
    db.commit()

    page = get_advisor_scorecard_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,advisor="scorecard-agent"))
    assert page.total == 1
    row = page.items[0]
    assert row.advisor_name == "scorecard-agent"
    assert row.active_lead_count == 1
    assert row.proposals_pending == 1
    assert row.completed_bookings == 1
    assert row.request_to_close_ratio_percent == 50.0


def test_passenger_demographics_page_filters_by_qualifier(db):
    user = _create_user(db, username="demographics-agent")
    military_passenger = Passenger(
        first_name="Alex",
        last_name="Veteran",
        email="alex@example.com",
        phone="555-0101",
        date_of_birth=date(1975, 6, 10),
        state_or_province="Texas",
        qualifiers=["Military"],
        created_by_id=user.id,
        is_active=True,
    )
    senior_passenger = Passenger(
        first_name="Pat",
        last_name="Senior",
        email="pat@example.com",
        phone="555-0102",
        date_of_birth=date(1960, 1, 20),
        qualifiers=["55+ Senior"],
        created_by_id=user.id,
        is_active=True,
    )
    db.add(military_passenger)
    db.add(senior_passenger)
    db.commit()

    page = get_passenger_demographics_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,qualifiers=("Military",)))
    matching = [row for row in page.items if row.passenger_name == "Alex Veteran"]
    assert len(matching) == 1
    assert matching[0].qualifiers == ["Military"]
    assert matching[0].state_of_residence == "Texas"

    educator_passenger = Passenger(
        first_name="Chris",
        last_name="Teacher",
        email="chris@example.com",
        phone="555-0103",
        date_of_birth=date(1988, 2, 2),
        qualifiers=["Educator"],
        created_by_id=user.id,
        is_active=True,
    )
    db.add(educator_passenger)
    db.commit()

    or_page = get_passenger_demographics_page(
        db,
        ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,qualifiers=("Military", "Educator")),
    )
    matched_names = {
        row.passenger_name
        for row in or_page.items
        if row.passenger_name in {"Alex Veteran", "Pat Senior", "Chris Teacher"}
    }
    assert matched_names == {"Alex Veteran", "Chris Teacher"}


def test_passenger_demographics_page_filters_by_state(db):
    user = _create_user(db, username="state-filter-agent")
    texas_passenger = Passenger(
        first_name="Alex",
        last_name="Veteran",
        email="alex@example.com",
        phone="555-0101",
        state_or_province="Texas",
        qualifiers=["Military"],
        created_by_id=user.id,
        is_active=True,
    )
    florida_passenger = Passenger(
        first_name="Blake",
        last_name="Sunshine",
        email="blake@example.com",
        phone="555-0102",
        state_or_province="Florida",
        qualifiers=["Educator"],
        created_by_id=user.id,
        is_active=True,
    )
    db.add(texas_passenger)
    db.add(florida_passenger)
    db.commit()

    page = get_passenger_demographics_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,state="Texas"))
    matching = [row for row in page.items if row.passenger_name == "Alex Veteran"]
    assert len(matching) == 1
    assert matching[0].state_of_residence == "Texas"

    florida_page = get_passenger_demographics_page(db, ReportQueryFilters(agency_id=DEFAULT_AGENCY_ID,state="Florida"))
    florida_matching = [row for row in florida_page.items if row.passenger_name == "Blake Sunshine"]
    assert len(florida_matching) == 1


def test_get_report_meta_includes_advisor_names(db):
    user = _create_user(db, username="meta-advisor")
    _create_request(db, user=user)
    db.commit()

    meta = get_report_meta(db, DEFAULT_AGENCY_ID)
    assert "meta-advisor" in meta.advisor_names


def test_get_report_meta_includes_residence_states(db):
    user = _create_user(db, username="meta-state-agent")
    db.add(
        Passenger(
            first_name="Sam",
            last_name="Resident",
            email="sam@example.com",
            state_or_province="Ohio",
            created_by_id=user.id,
            is_active=True,
        )
    )
    db.commit()

    meta = get_report_meta(db, DEFAULT_AGENCY_ID)
    assert "Ohio" in meta.residence_states
