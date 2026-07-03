from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from email.utils import parseaddr

from app.agency_email_branding import AgencyEmailBranding
from app.branding import BRAND_NAME
from app.config import Settings
from app.email_config import (
    APP_ENV_DEVELOPMENT,
    APP_ENV_PRODUCTION,
    APP_ENV_STAGING,
    DEVELOPMENT_MAILPIT_HOST,
    DEVELOPMENT_MAILPIT_PORT,
    DevelopmentEmailIsolationError,
    EmailDeliverySettings,
    resolve_email_delivery_settings,
)
from app.models import AgencyEmailLog
from app.research_proposal_email import (
    RESEARCH_PROPOSAL_CONTENT_END,
    RESEARCH_PROPOSAL_CONTENT_START,
    build_research_proposal_email_html,
)
from app.services.email_service import (
    EMAIL_STATUS_FAILED,
    EMAIL_STATUS_SENT,
    EmailDeliveryService,
    extract_communication_html_content,
    render_email_base_html,
)
from app.tenant_constants import DEFAULT_AGENCY_ID


def _sample_cruise(**overrides):
    base = {
        "departure_date": date(2026, 7, 10),
        "return_date": date(2026, 7, 17),
        "cruise_line": "Royal Caribbean",
        "ship": "Wonder of the Seas",
        "number_of_nights": 7,
        "itinerary_name": "Western Caribbean",
        "itinerary_details": "Day 1: Miami\nDay 2: At sea",
        "room_category": "Veranda",
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


def _development_delivery(**overrides) -> EmailDeliverySettings:
    delivery = resolve_email_delivery_settings(Settings(app_env=APP_ENV_DEVELOPMENT))
    if not overrides:
        return delivery
    return EmailDeliverySettings(
        environment=overrides.get("environment", delivery.environment),
        backend=overrides.get("backend", delivery.backend),
        smtp_host=overrides.get("smtp_host", delivery.smtp_host),
        smtp_port=overrides.get("smtp_port", delivery.smtp_port),
        smtp_username=overrides.get("smtp_username", delivery.smtp_username),
        smtp_password=overrides.get("smtp_password", delivery.smtp_password),
        smtp_use_tls=overrides.get("smtp_use_tls", delivery.smtp_use_tls),
        from_address=overrides.get("from_address", delivery.from_address),
        api_key=overrides.get("api_key", delivery.api_key),
        api_provider=overrides.get("api_provider", delivery.api_provider),
    )


def _send_kwargs(**overrides):
    base = {
        "agency_id": DEFAULT_AGENCY_ID,
        "user_id": "1",
        "user_name": "Jane Agent",
        "user_email": "jane.agent@agency.com",
        "recipient": "client@example.com",
        "email_type": "research_proposal",
        "subject": "Cruise Proposal – Caribbean (2 options)",
        "html_content": "<p>Proposal body</p>",
        "travel_request_id": None,
    }
    base.update(overrides)
    return base


# --- extract_communication_html_content ---


def test_extract_communication_html_content_keeps_full_proposal_body():
    html = build_research_proposal_email_html(
        intro="Here are your options.",
        closing="Reply when ready.",
        cruises=[_sample_cruise(), _sample_cruise(cruise_line="Celebrity", ship="Ascent", room_category="Suite")],
    )

    extracted = extract_communication_html_content(html)

    assert "Here are your options." in extracted
    assert "Reply when ready." in extracted
    assert "Guests in room" in extracted
    assert "Included with this option" in extracted
    assert "Gratuities / tips included" in extracted
    assert "Celebrity" in extracted
    assert "Suite" in extracted
    assert "Your cruise options" not in extracted


def test_extract_communication_html_content_handles_legacy_proposal_without_markers():
    html = build_research_proposal_email_html(
        intro="Legacy draft intro.",
        closing="Legacy draft closing.",
        cruises=[_sample_cruise(), _sample_cruise(cruise_line="Celebrity", ship="Ascent")],
    )
    legacy_html = html.replace(RESEARCH_PROPOSAL_CONTENT_START, "").replace(RESEARCH_PROPOSAL_CONTENT_END, "")

    extracted = extract_communication_html_content(legacy_html)

    assert "Legacy draft intro." in extracted
    assert "Legacy draft closing." in extracted
    assert "Included with this option" in extracted
    assert "Celebrity" in extracted


def test_extract_communication_html_content_returns_fragment_as_is():
    fragment = "<p>Plain HTML fragment</p>"
    assert extract_communication_html_content(fragment) == fragment


def _sample_email_branding(**overrides) -> AgencyEmailBranding:
    base = {
        "agency_id": DEFAULT_AGENCY_ID,
        "agency_name": "Ocean & Voyages",
        "brand_logo_url": None,
        "brand_logo_absolute_url": None,
        "primary_color": "#0d5c75",
        "secondary_color": "#17a2b8",
        "primary_text_color": "#ffffff",
        "email_signature_block": None,
    }
    base.update(overrides)
    return AgencyEmailBranding(**base)


def test_render_email_base_html_escapes_agent_and_agency_names():
    html = render_email_base_html(
        content="<p>Body</p>",
        agent_name='Jane <script>alert("x")</script>',
        branding=_sample_email_branding(agency_name="Ocean & Voyages"),
    )

    assert "<script>" not in html
    assert "Jane &lt;script&gt;" in html
    assert "Ocean &amp; Voyages" in html
    assert "<p>Body</p>" in html


def test_render_email_base_html_includes_signature_and_branded_header():
    html = render_email_base_html(
        content="<p>Body</p>",
        agent_name="Jane Agent",
        branding=_sample_email_branding(
            agency_name="Cruise Seakers Travel LLC",
            email_signature_block="<p>Best regards,<br/>Jane</p>",
        ),
    )

    assert "Cruise Seakers Travel LLC" in html
    assert "Best regards" in html
    assert BRAND_NAME in html


# --- Header construction ---


def test_build_message_sets_display_from_sender_and_reply_to():
    service = EmailDeliveryService(SimpleNamespace(), delivery_settings=_development_delivery())
    message = service._build_message(
        recipient="client@example.com",
        subject="Your cruise proposal",
        html_content="<p>Hello</p>",
        user_name="Jane Agent",
        user_email="jane.agent@agency.com",
    )

    display_name, from_address = parseaddr(message["From"])
    assert display_name == f"Jane Agent via {BRAND_NAME}"
    assert from_address == "notifications@sailspipeline.com"
    assert message["Sender"] == "notifications@sailspipeline.com"
    assert message["Reply-To"] == "jane.agent@agency.com"
    assert message["To"] == "client@example.com"
    assert message["Subject"] == "Your cruise proposal"


def test_format_from_header_strips_agent_name_whitespace():
    service = EmailDeliveryService(SimpleNamespace(), delivery_settings=_development_delivery())

    formatted = service._format_from_header("  Jane Agent  ")

    display_name, from_address = parseaddr(formatted)
    assert display_name == f"Jane Agent via {BRAND_NAME}"
    assert from_address == "notifications@sailspipeline.com"


def test_build_message_uses_staging_from_address_when_configured():
    delivery = resolve_email_delivery_settings(
        Settings(
            app_env=APP_ENV_STAGING,
            email_api_key_staging="re_staging_test",
            email_from_address_staging="staging@mail.sailspipeline.com",
        )
    )
    service = EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)
    message = service._build_message(
        recipient="client@example.com",
        subject="Staging proposal",
        html_content="<p>Hi</p>",
        user_name="Jane Agent",
        user_email="jane.agent@agency.com",
    )

    _, from_address = parseaddr(message["From"])
    assert message["Sender"] == "staging@mail.sailspipeline.com"
    assert from_address == "staging@mail.sailspipeline.com"


# --- Environment toggles ---


def test_development_settings_default_to_mailpit_smtp():
    delivery = resolve_email_delivery_settings(
        Settings(
            app_env=APP_ENV_DEVELOPMENT,
            email_backend="api",
            email_host="smtp.sendgrid.net",
            email_port=587,
            email_api_key="live-secret",
        )
    )

    assert delivery.backend == "smtp"
    assert delivery.smtp_host == DEVELOPMENT_MAILPIT_HOST
    assert delivery.smtp_port == DEVELOPMENT_MAILPIT_PORT
    assert delivery.api_key is None


def test_email_delivery_service_init_uses_settings_when_no_override(monkeypatch):
    import app.config as config_module

    monkeypatch.setattr(
        config_module,
        "settings",
        Settings(app_env=APP_ENV_DEVELOPMENT, email_api_key="must-be-ignored"),
    )
    service = EmailDeliveryService(SimpleNamespace())

    assert service._delivery.backend == "smtp"
    assert service._delivery.smtp_host == DEVELOPMENT_MAILPIT_HOST


def test_development_init_rejects_api_backend_override():
    delivery = _development_delivery(backend="api")

    with pytest.raises(DevelopmentEmailIsolationError, match="requires SMTP transport"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


def test_development_init_rejects_loaded_api_credentials():
    delivery = _development_delivery(api_key="re_live_secret")

    with pytest.raises(DevelopmentEmailIsolationError, match="forbids loading cloud email API credentials"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


def test_development_init_rejects_non_local_smtp_host():
    delivery = _development_delivery(smtp_host="smtp.sendgrid.net")

    with pytest.raises(DevelopmentEmailIsolationError, match="is not allowed"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


def test_development_blocks_external_api_calls():
    service = EmailDeliveryService(SimpleNamespace(), delivery_settings=_development_delivery())

    with pytest.raises(DevelopmentEmailIsolationError, match="blocked when APP_ENV=development"):
        asyncio.run(
            service._send_via_api(
                recipient="client@example.com",
                subject="Test",
                html_content="<p>Hi</p>",
                user_name="Agent",
                user_email="agent@example.com",
            )
        )


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_development_send_routes_to_mailpit_smtp(mock_send, db, test_user):
    mock_send.return_value = {}
    service = EmailDeliveryService(db, delivery_settings=_development_delivery())

    success = asyncio.run(
        service.send_transactional_email(
            **_send_kwargs(user_id=str(test_user.id)),
        )
    )

    assert success is True
    mock_send.assert_awaited_once()
    assert mock_send.await_args.kwargs["hostname"] == DEVELOPMENT_MAILPIT_HOST
    assert mock_send.await_args.kwargs["port"] == DEVELOPMENT_MAILPIT_PORT


def test_staging_resolves_to_api_backend():
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_STAGING, email_api_key_staging="re_staging_test")
    )

    assert delivery.backend == "api"
    assert delivery.api_key == "re_staging_test"


def test_production_resolves_to_api_backend():
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_PRODUCTION, email_api_key="re_live_production")
    )

    assert delivery.backend == "api"
    assert delivery.api_key == "re_live_production"


# --- Database auditing ---


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_successful_send_writes_sent_audit_log(mock_send, db, test_user):
    mock_send.return_value = {}
    service = EmailDeliveryService(db, delivery_settings=_development_delivery())
    payload = _send_kwargs(user_id=str(test_user.id))

    success = asyncio.run(service.send_transactional_email(**payload))

    assert success is True
    log = (
        db.query(AgencyEmailLog)
        .filter(
            AgencyEmailLog.recipient_email == payload["recipient"],
            AgencyEmailLog.subject_line == payload["subject"],
        )
        .one()
    )
    assert log.status == EMAIL_STATUS_SENT
    assert log.error_message is None
    assert log.agency_id == DEFAULT_AGENCY_ID
    assert log.user_id == test_user.id
    assert log.travel_request_id is None
    assert log.email_type == "research_proposal"
    assert log.recipient_email == "client@example.com"


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_failed_send_writes_failed_audit_log_with_error_message(mock_send, db, test_user):
    mock_send.side_effect = ConnectionError("Mailpit unreachable on port 1025")
    service = EmailDeliveryService(db, delivery_settings=_development_delivery())
    payload = _send_kwargs(user_id=str(test_user.id))

    success = asyncio.run(service.send_transactional_email(**payload))

    assert success is False
    log = (
        db.query(AgencyEmailLog)
        .filter(
            AgencyEmailLog.recipient_email == payload["recipient"],
            AgencyEmailLog.subject_line == payload["subject"],
        )
        .one()
    )
    assert log.status == EMAIL_STATUS_FAILED
    assert "Mailpit unreachable on port 1025" in (log.error_message or "")
    assert log.agency_id == DEFAULT_AGENCY_ID
    assert log.user_id == test_user.id


def test_staging_api_failure_writes_failed_audit_log(db, test_user):
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_STAGING, email_api_key_staging="re_staging_test")
    )
    service = EmailDeliveryService(db, delivery_settings=delivery)
    payload = _send_kwargs(user_id=str(test_user.id))

    success = asyncio.run(service.send_transactional_email(**payload))

    assert success is False
    log = (
        db.query(AgencyEmailLog)
        .filter(
            AgencyEmailLog.recipient_email == payload["recipient"],
            AgencyEmailLog.subject_line == payload["subject"],
        )
        .one()
    )
    assert log.status == EMAIL_STATUS_FAILED
    assert log.error_message is not None
    assert "provider SDK is not wired" in log.error_message


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_audit_log_truncates_long_error_messages(mock_send, db, test_user):
    mock_send.side_effect = RuntimeError("x" * 5000)
    service = EmailDeliveryService(db, delivery_settings=_development_delivery())

    asyncio.run(service.send_transactional_email(**_send_kwargs(user_id=str(test_user.id))))

    log = db.query(AgencyEmailLog).order_by(AgencyEmailLog.created_at.desc()).first()
    assert log is not None
    assert log.status == EMAIL_STATUS_FAILED
    assert len(log.error_message or "") == 4000
