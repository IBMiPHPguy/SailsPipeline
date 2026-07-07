from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.agency_email_branding import AgencyEmailBranding
from app.research_proposal_email import build_research_proposal_email_html


def _sample_cruise(**overrides):
    base = {
        "departure_date": date(2026, 7, 10),
        "return_date": date(2026, 7, 17),
        "cruise_line": "Royal Caribbean",
        "ship": "Wonder of the Seas",
        "number_of_nights": 7,
        "itinerary_name": "Western Caribbean",
        "itinerary_details": "Day 1: Miami\nDay 2: At sea",
        "room_category": "Balcony",
        "room_number": "TBD",
        "passengers_in_room": 2,
        "deposit_due_date": date(2026, 5, 1),
        "final_payment_due_date": date(2026, 6, 1),
        "deposit_amount": Decimal("500.00"),
        "cost": Decimal("4200.00"),
        "includes": {
            "drink_package": {"included": True, "name": "Deluxe"},
            "wifi": {"included": False, "name": ""},
            "tips": True,
            "excursion": False,
            "excursion_credit": {"included": False, "amount": None},
            "onboard_credit": {"included": True, "amount": "100.00"},
            "gift_obc": {"included": False, "amount": None},
        },
    }
    base.update(overrides)
    if "passenger_links" not in base:
        base["passenger_links"] = []
    return SimpleNamespace(**base)


def test_build_research_proposal_email_html_includes_intro_and_cruise_details():
    html = build_research_proposal_email_html(
        intro="Here are a few options for your trip.",
        closing="Let me know which option you prefer.",
        cruises=[_sample_cruise()],
    )

    assert "<html" in html.lower()
    assert "Here are a few options for your trip." in html
    assert "Let me know which option you prefer." in html
    assert "Royal Caribbean" in html
    assert "Day 1: Miami" in html
    assert "SailsPipeline" in html
    assert "Gratuities / tips included" in html


def test_build_research_proposal_email_html_uses_tenant_branding_when_provided():
    branding = AgencyEmailBranding(
        agency_id="agency-1",
        agency_name="Harbor Cruises LLC",
        brand_logo_url=None,
        brand_logo_absolute_url=None,
        primary_color="#0d5c75",
        secondary_color="#17a2b8",
        primary_text_color="#ffffff",
        email_signature_block=None,
    )
    html = build_research_proposal_email_html(
        intro="Intro",
        closing="Closing",
        cruises=[_sample_cruise()],
        branding=branding,
    )

    assert "Harbor Cruises LLC" in html
    assert "SailsPipeline" not in html


def test_build_research_proposal_email_html_falls_back_to_itinerary_name():
    html = build_research_proposal_email_html(
        intro="Intro",
        closing="Closing",
        cruises=[_sample_cruise(itinerary_details="")],
    )

    assert "Western Caribbean" in html


def test_build_research_proposal_email_html_renders_optional_inclusions():
    html = build_research_proposal_email_html(
        intro="",
        closing="Thanks",
        cruises=[
            _sample_cruise(
                includes={
                    "drink_package": {"included": False, "name": ""},
                    "wifi": {"included": True, "name": "Premium"},
                    "specialty_dining": {"included": True, "name": "Chef's Table"},
                    "tips": False,
                    "excursion": True,
                    "excursion_credit": {"included": True, "amount": "75.00"},
                    "onboard_credit": {"included": True, "amount": "100.00"},
                    "gift_obc": {"included": True, "amount": "50.00"},
                }
            )
        ],
    )

    assert "Wi-Fi: Premium" in html
    assert "Specialty dining: Chef's Table" in html
    assert "Shore excursion included" in html
    assert "Excursion credit" in html
    assert "Cruise line OBC" in html
    assert "Gift OBC" in html


def test_build_research_proposal_email_html_renders_multi_room_details():
    cruise = _sample_cruise(
        deposit_amount=Decimal("1000.00"),
        cost=Decimal("8400.00"),
        cabin_rooms=[
            {
                "room_category": "Balcony",
                "room_number": "1204",
                "passengers_in_room": 2,
                "deposit_amount": "500.00",
                "commission": "0",
                "cost": "4200.00",
                "includes": {
                    "drink_package": {"included": True, "name": "Deluxe"},
                    "wifi": {"included": False, "name": None},
                    "specialty_dining": {"included": False, "name": None},
                    "tips": True,
                    "excursion": False,
                    "excursion_credit": {"included": False, "amount": None},
                    "onboard_credit": {"included": False, "amount": None},
                    "gift_obc": {"included": False, "amount": None},
                },
            },
            {
                "room_category": "Interior",
                "room_number": "8210",
                "passengers_in_room": 2,
                "deposit_amount": "500.00",
                "commission": "0",
                "cost": "4200.00",
                "includes": {
                    "drink_package": {"included": False, "name": None},
                    "wifi": {"included": True, "name": "Surf"},
                    "specialty_dining": {"included": False, "name": None},
                    "tips": False,
                    "excursion": False,
                    "excursion_credit": {"included": False, "amount": None},
                    "onboard_credit": {"included": False, "amount": None},
                    "gift_obc": {"included": False, "amount": None},
                },
            },
        ],
    )
    html = build_research_proposal_email_html(
        intro="Two cabins for your family.",
        closing="Reply with your favorite.",
        cruises=[cruise],
        cabins_needed=2,
    )

    assert "Rooms in this option" in html
    assert "Room 1" in html
    assert "Room 2" in html
    assert "Drink package: Deluxe" in html
    assert "Wi-Fi: Surf" in html
    assert "Overall pricing" in html
    assert "$8,400.00" in html
