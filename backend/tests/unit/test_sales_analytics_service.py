from datetime import date, datetime
from decimal import Decimal

from app.constants import (
    PRIMARY_CLOSE_REASON,
    PROPOSED_CRUISE_REJECTION_REASON_ITINERARY,
    PROPOSED_CRUISE_REJECTION_REASON_PRICE,
    PROPOSED_CRUISE_STATUS_ACCEPTED,
    PROPOSED_CRUISE_STATUS_DEPOSITED,
    PROPOSED_CRUISE_STATUS_REJECTED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_OPEN,
    SALES_REJECTION_SEGMENT_CLOSED_LOST,
    SALES_REJECTION_SEGMENT_OPEN_ACTIVE,
)
from app.models import ProposedCruise, TravelRequest, User
from app.security import hash_password
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.services.sales_analytics_service import get_sales_analytics, get_sales_analytics_key_metrics_year


def _create_user(db, *, username: str) -> User:
    user = User(username=username, email=f"{username}@example.com", password_hash=hash_password("ValidPass1!"))
    db.add(user)
    db.flush()
    return user


def _create_open_request(db, *, user: User) -> TravelRequest:
    request = TravelRequest(
        first_name="Alex",
        last_name="Rivera",
        email="alex@example.com",
        phone="5551234567",
        cruise_lines=["Princess Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        close_reason=None,
        created_by=user,
        updated_by=user,
    )
    db.add(request)
    db.flush()
    return request


def test_sales_analytics_commission_timeline_and_funnel(db):
    user = _create_user(db, username="analytics-agent")
    request = _create_open_request(db, user=user)

    accepted = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 9, 15),
        cruise_line="Princess Cruises",
        ship="Sky Princess",
        number_of_nights=7,
        itinerary_name="Eastern Caribbean",
        room_category="Balcony",
        room_number="B210",
        passengers_in_room=2,
        deposit_amount=Decimal("500.00"),
        deposit_due_date=date(2026, 6, 1),
        final_payment_due_date=date(2026, 8, 1),
        cost=Decimal("4200.00"),
        cabin_rooms=[{"commission": "350.00"}],
        status=PROPOSED_CRUISE_STATUS_ACCEPTED,
        created_by=user,
        updated_by=user,
    )
    rejected = ProposedCruise(
        travel_request_id=request.id,
        departure_date=date(2026, 10, 1),
        cruise_line="Celebrity Cruises",
        ship="Ascent",
        number_of_nights=7,
        itinerary_name="Western Caribbean",
        room_category="Balcony",
        room_number="7204",
        passengers_in_room=2,
        deposit_amount=Decimal("400.00"),
        deposit_due_date=date(2026, 6, 15),
        final_payment_due_date=date(2026, 8, 15),
        cost=Decimal("3900.00"),
        cabin_rooms=[{"commission": "0"}],
        status=PROPOSED_CRUISE_STATUS_REJECTED,
        rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
        created_by=user,
        updated_by=user,
    )
    db.add_all([accepted, rejected])
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    assert analytics.total_commission_forecast == 350.0
    assert analytics.win_rate_percent is None
    assert any(
        item.segment == SALES_REJECTION_SEGMENT_OPEN_ACTIVE
        and item.reason == PROPOSED_CRUISE_REJECTION_REASON_PRICE
        and item.count == 1
        for item in analytics.rejection_reasons
    )
    assert any(month.total_commission == 350.0 for month in analytics.commission_timeline)
    assert len(analytics.cruise_line_shares) == 1
    assert analytics.cruise_line_shares[0].cruise_line == "Princess Cruises"
    assert analytics.cruise_line_shares[0].booking_count == 1
    assert analytics.current_year_summary.total_sales_booked == 4200.0
    assert analytics.current_year_summary.total_sales_lost == 0.0
    assert analytics.current_year_summary.average_commission_rate_percent == 8.3
    assert analytics.current_year_summary.win_rate_percent is None
    assert analytics.current_year_summary.year == date.today().year
    assert analytics.key_metrics_prior_years == []
    assert any(stage.label == "Active leads" and stage.count == 1 for stage in analytics.funnel_stages)


def test_sales_analytics_cruise_line_shares_aggregate_all_booked_cruises(db):
    user = _create_user(db, username="analytics-deposited-share")
    request = _create_open_request(db, user=user)

    db.add_all(
        [
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 9, 15),
                cruise_line="Princess Cruises",
                ship="Sky Princess",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="B210",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 8, 1),
                cost=Decimal("4200.00"),
                cabin_rooms=[{"commission": "350.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2026, 10, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="7204",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2026, 6, 15),
                final_payment_due_date=date(2026, 8, 15),
                cost=Decimal("5100.00"),
                cabin_rooms=[{"commission": "510.00"}],
                status=PROPOSED_CRUISE_STATUS_DEPOSITED,
                created_by=user,
                updated_by=user,
            ),
        ]
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    assert len(analytics.cruise_line_shares) == 2
    shares_by_line = {share.cruise_line: share for share in analytics.cruise_line_shares}
    princess = shares_by_line["Princess Cruises"]
    celebrity = shares_by_line["Celebrity Cruises"]
    assert princess.booking_count == 1
    assert princess.total_booking_amount == 4200.0
    assert princess.total_commission == 350.0
    assert princess.share_percent == 50.0
    assert celebrity.booking_count == 1
    assert celebrity.total_booking_amount == 5100.0
    assert celebrity.total_commission == 510.0
    assert celebrity.share_percent == 50.0
    assert analytics.current_year_summary.total_sales_booked == 9300.0
    assert analytics.current_year_summary.average_commission_rate_percent == 9.2


def test_sales_analytics_year_summaries_use_book_and_reject_dates_not_departure(db):
    user = _create_user(db, username="analytics-event-dates")
    request = _create_open_request(db, user=user)

    db.add_all(
        [
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2028, 9, 15),
                cruise_line="Princess Cruises",
                ship="Sky Princess",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="B210",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2028, 6, 1),
                final_payment_due_date=date(2028, 8, 1),
                cost=Decimal("5000.00"),
                cabin_rooms=[{"commission": "400.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
                updated_at=datetime(2026, 3, 15, 12, 0, 0),
            ),
            ProposedCruise(
                travel_request_id=request.id,
                departure_date=date(2028, 10, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="7204",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2028, 6, 15),
                final_payment_due_date=date(2028, 8, 15),
                cost=Decimal("4500.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
                updated_at=datetime(2026, 4, 10, 12, 0, 0),
            ),
        ]
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)
    current_year = date.today().year

    assert analytics.current_year_summary.year == current_year
    assert analytics.current_year_summary.total_sales_booked == 5000.0
    assert analytics.current_year_summary.total_sales_lost == 0.0
    assert analytics.current_year_summary.average_commission_rate_percent == 8.0
    assert analytics.current_year_summary.win_rate_percent is None
    assert current_year not in analytics.key_metrics_prior_years


def test_sales_analytics_win_rate_uses_closed_requests_only(db):
    user = _create_user(db, username="analytics-win-rate")

    open_booked = _create_open_request(db, user=user)
    open_rejected_only = TravelRequest(
        first_name="Sam",
        last_name="Lee",
        email="sam@example.com",
        phone="5559876543",
        cruise_lines=["Royal Caribbean International"],
        excluded_cruise_lines=[],
        destination="Alaska",
        destination_details=None,
        departure_date=date(2026, 7, 1),
        return_date=date(2026, 7, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_OPEN,
        close_reason=None,
        created_by=user,
        updated_by=user,
    )
    closed_won = TravelRequest(
        first_name="Terry",
        last_name="Nguyen",
        email="terry@example.com",
        phone="5551112222",
        cruise_lines=["Celebrity Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Western"]},
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason=PRIMARY_CLOSE_REASON,
        created_by=user,
        updated_by=user,
    )
    closed_lost = TravelRequest(
        first_name="Pat",
        last_name="Stone",
        email="pat@example.com",
        phone="5553334444",
        cruise_lines=["Princess Cruises"],
        excluded_cruise_lines=[],
        destination="Europe",
        destination_details=None,
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 15),
        cabin_types=["Interior"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason="No response",
        created_by=user,
        updated_by=user,
    )
    db.add_all([open_rejected_only, closed_won, closed_lost])
    db.flush()

    db.add_all(
        [
            ProposedCruise(
                travel_request_id=open_booked.id,
                departure_date=date(2026, 9, 15),
                cruise_line="Princess Cruises",
                ship="Sky Princess",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="B210",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 8, 1),
                cost=Decimal("4200.00"),
                cabin_rooms=[{"commission": "350.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=open_booked.id,
                departure_date=date(2026, 10, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="7204",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2026, 6, 15),
                final_payment_due_date=date(2026, 8, 15),
                cost=Decimal("3900.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=open_rejected_only.id,
                departure_date=date(2026, 8, 1),
                cruise_line="Royal Caribbean International",
                ship="Icon",
                number_of_nights=7,
                itinerary_name="Alaska",
                room_category="Balcony",
                room_number="1204",
                passengers_in_room=2,
                deposit_amount=Decimal("300.00"),
                deposit_due_date=date(2026, 5, 1),
                final_payment_due_date=date(2026, 7, 1),
                cost=Decimal("3100.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_won.id,
                departure_date=date(2026, 5, 10),
                cruise_line="Celebrity Cruises",
                ship="Edge",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="9102",
                passengers_in_room=2,
                deposit_amount=Decimal("450.00"),
                deposit_due_date=date(2026, 3, 1),
                final_payment_due_date=date(2026, 4, 1),
                cost=Decimal("4000.00"),
                cabin_rooms=[{"commission": "250.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
            ),
        ]
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    # 1 closed win + 1 closed loss = 50%; open requests are excluded
    assert analytics.win_rate_percent == 50.0
    assert analytics.current_year_summary.total_sales_booked == 4000.0
    assert analytics.current_year_summary.total_sales_lost == 0.0
    assert analytics.current_year_summary.average_commission_rate_percent == 6.2
    assert analytics.current_year_summary.win_rate_percent == 50.0


def test_sales_analytics_rejection_drivers_split_open_and_closed_leads(db):
    user = _create_user(db, username="analytics-rejection-drivers")

    open_request = _create_open_request(db, user=user)
    closed_lost = TravelRequest(
        first_name="Pat",
        last_name="Stone",
        email="pat@example.com",
        phone="5553334444",
        cruise_lines=["Princess Cruises"],
        excluded_cruise_lines=[],
        destination="Europe",
        destination_details=None,
        departure_date=date(2026, 6, 1),
        return_date=date(2026, 6, 15),
        cabin_types=["Interior"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason="No response",
        created_by=user,
        updated_by=user,
    )
    closed_won = TravelRequest(
        first_name="Terry",
        last_name="Nguyen",
        email="terry@example.com",
        phone="5551112222",
        cruise_lines=["Celebrity Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Western"]},
        departure_date=date(2026, 5, 1),
        return_date=date(2026, 5, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason=PRIMARY_CLOSE_REASON,
        created_by=user,
        updated_by=user,
    )
    db.add_all([closed_lost, closed_won])
    db.flush()

    db.add_all(
        [
            ProposedCruise(
                travel_request_id=open_request.id,
                departure_date=date(2026, 9, 1),
                cruise_line="Princess Cruises",
                ship="Sky Princess",
                number_of_nights=7,
                itinerary_name="Alaska",
                room_category="Balcony",
                room_number="1010",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 8, 1),
                cost=Decimal("4200.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_lost.id,
                departure_date=date(2026, 7, 1),
                cruise_line="Princess Cruises",
                ship="Discovery",
                number_of_nights=7,
                itinerary_name="Mediterranean",
                room_category="Balcony",
                room_number="2020",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2026, 5, 1),
                final_payment_due_date=date(2026, 6, 1),
                cost=Decimal("3900.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_ITINERARY,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_won.id,
                departure_date=date(2026, 5, 10),
                cruise_line="Celebrity Cruises",
                ship="Edge",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="9102",
                passengers_in_room=2,
                deposit_amount=Decimal("450.00"),
                deposit_due_date=date(2026, 3, 1),
                final_payment_due_date=date(2026, 4, 1),
                cost=Decimal("4000.00"),
                cabin_rooms=[{"commission": "250.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_won.id,
                departure_date=date(2026, 6, 1),
                cruise_line="Royal Caribbean International",
                ship="Icon",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="8204",
                passengers_in_room=2,
                deposit_amount=Decimal("300.00"),
                deposit_due_date=date(2026, 4, 1),
                final_payment_due_date=date(2026, 5, 1),
                cost=Decimal("3500.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
        ]
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    assert any(
        item.segment == SALES_REJECTION_SEGMENT_OPEN_ACTIVE
        and item.reason == PROPOSED_CRUISE_REJECTION_REASON_PRICE
        and item.count == 1
        for item in analytics.rejection_reasons
    )
    assert any(
        item.segment == SALES_REJECTION_SEGMENT_CLOSED_LOST
        and item.reason == PROPOSED_CRUISE_REJECTION_REASON_ITINERARY
        and item.count == 1
        for item in analytics.rejection_reasons
    )
    assert not any(
        item.segment == SALES_REJECTION_SEGMENT_CLOSED_LOST and item.reason == PROPOSED_CRUISE_REJECTION_REASON_PRICE
        for item in analytics.rejection_reasons
    )


def test_sales_analytics_key_metrics_prior_years_load_on_demand(db):
    user = _create_user(db, username="analytics-prior-year")
    request = _create_open_request(db, user=user)
    prior_year = date.today().year - 1

    db.add(
        ProposedCruise(
            travel_request_id=request.id,
            departure_date=date(prior_year, 9, 15),
            cruise_line="Princess Cruises",
            ship="Sky Princess",
            number_of_nights=7,
            itinerary_name="Eastern Caribbean",
            room_category="Balcony",
            room_number="B210",
            passengers_in_room=2,
            deposit_amount=Decimal("500.00"),
            deposit_due_date=date(prior_year, 6, 1),
            final_payment_due_date=date(prior_year, 8, 1),
            cost=Decimal("3100.00"),
            cabin_rooms=[{"commission": "250.00"}],
            status=PROPOSED_CRUISE_STATUS_DEPOSITED,
            created_by=user,
            updated_by=user,
            updated_at=datetime(prior_year, 5, 10, 12, 0, 0),
        )
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    assert prior_year in analytics.key_metrics_prior_years
    assert analytics.current_year_summary.year == date.today().year
    assert analytics.current_year_summary.total_sales_booked == 0.0

    prior_summary = get_sales_analytics_key_metrics_year(db, prior_year, DEFAULT_AGENCY_ID)
    assert prior_summary.year == prior_year
    assert prior_summary.total_sales_booked == 3100.0
    assert prior_summary.average_commission_rate_percent == 8.1


def _create_closed_request(db, *, user: User, close_reason: str = "No response") -> TravelRequest:
    request = TravelRequest(
        first_name="Casey",
        last_name="Morgan",
        email="casey@example.com",
        phone="5554445555",
        cruise_lines=["Princess Cruises"],
        excluded_cruise_lines=[],
        destination="Caribbean",
        destination_details={"caribbean_regions": ["Eastern"]},
        departure_date=date(2026, 8, 1),
        return_date=date(2026, 8, 8),
        cabin_types=["Balcony"],
        qualifiers=[],
        passengers=2,
        cabins_needed=1,
        status=REQUEST_STATUS_CLOSED,
        close_reason=close_reason,
        created_by=user,
        updated_by=user,
    )
    db.add(request)
    db.flush()
    return request


def test_sales_analytics_lost_sales_from_closed_requests(db):
    user = _create_user(db, username="analytics-lost-sales")

    single_quote_lost = _create_closed_request(db, user=user)
    multi_quote_lost = _create_closed_request(db, user=user, close_reason="Price")
    zero_quote_lost = _create_closed_request(db, user=user, close_reason="Timing")
    no_quote_lost = _create_closed_request(db, user=user, close_reason="No response")
    closed_won = _create_closed_request(db, user=user, close_reason=PRIMARY_CLOSE_REASON)

    db.add_all(
        [
            ProposedCruise(
                travel_request_id=single_quote_lost.id,
                departure_date=date(2026, 9, 1),
                cruise_line="Princess Cruises",
                ship="Sky Princess",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="1010",
                passengers_in_room=2,
                deposit_amount=Decimal("500.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 8, 1),
                cost=Decimal("4200.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=multi_quote_lost.id,
                departure_date=date(2026, 10, 1),
                cruise_line="Celebrity Cruises",
                ship="Ascent",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="2020",
                passengers_in_room=2,
                deposit_amount=Decimal("400.00"),
                deposit_due_date=date(2026, 6, 15),
                final_payment_due_date=date(2026, 8, 15),
                cost=Decimal("5100.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=multi_quote_lost.id,
                departure_date=date(2026, 11, 1),
                cruise_line="Royal Caribbean International",
                ship="Icon",
                number_of_nights=7,
                itinerary_name="Eastern Caribbean",
                room_category="Balcony",
                room_number="3030",
                passengers_in_room=2,
                deposit_amount=Decimal("350.00"),
                deposit_due_date=date(2026, 7, 1),
                final_payment_due_date=date(2026, 9, 1),
                cost=Decimal("3900.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_ITINERARY,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=zero_quote_lost.id,
                departure_date=date(2026, 8, 15),
                cruise_line="Princess Cruises",
                ship="Discovery",
                number_of_nights=7,
                itinerary_name="Alaska",
                room_category="Balcony",
                room_number="4040",
                passengers_in_room=2,
                deposit_amount=Decimal("0.00"),
                deposit_due_date=date(2026, 6, 1),
                final_payment_due_date=date(2026, 8, 1),
                cost=Decimal("0.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_won.id,
                departure_date=date(2026, 5, 10),
                cruise_line="Celebrity Cruises",
                ship="Edge",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="9102",
                passengers_in_room=2,
                deposit_amount=Decimal("450.00"),
                deposit_due_date=date(2026, 3, 1),
                final_payment_due_date=date(2026, 4, 1),
                cost=Decimal("4000.00"),
                cabin_rooms=[{"commission": "250.00"}],
                status=PROPOSED_CRUISE_STATUS_ACCEPTED,
                created_by=user,
                updated_by=user,
            ),
            ProposedCruise(
                travel_request_id=closed_won.id,
                departure_date=date(2026, 6, 1),
                cruise_line="Royal Caribbean International",
                ship="Icon",
                number_of_nights=7,
                itinerary_name="Western Caribbean",
                room_category="Balcony",
                room_number="8204",
                passengers_in_room=2,
                deposit_amount=Decimal("300.00"),
                deposit_due_date=date(2026, 4, 1),
                final_payment_due_date=date(2026, 5, 1),
                cost=Decimal("3500.00"),
                cabin_rooms=[{"commission": "0"}],
                status=PROPOSED_CRUISE_STATUS_REJECTED,
                rejection_reason=PROPOSED_CRUISE_REJECTION_REASON_PRICE,
                created_by=user,
                updated_by=user,
            ),
        ]
    )
    db.commit()

    analytics = get_sales_analytics(db, DEFAULT_AGENCY_ID)

    # 4200 single quote + 3900 lowest of two quotes; zero-only and no-quote closes excluded; booked close excluded
    assert analytics.current_year_summary.total_sales_lost == 8100.0
