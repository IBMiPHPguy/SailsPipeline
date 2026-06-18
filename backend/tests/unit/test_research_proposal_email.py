from datetime import date
from decimal import Decimal
from types import SimpleNamespace

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
    assert "Gratuities / tips included" in html


def test_build_research_proposal_email_html_falls_back_to_itinerary_name():
    html = build_research_proposal_email_html(
        intro="Intro",
        closing="Closing",
        cruises=[_sample_cruise(itinerary_details="")],
    )

    assert "Western Caribbean" in html
