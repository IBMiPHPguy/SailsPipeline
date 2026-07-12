from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from email.utils import parseaddr
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    render_email_logo_only_base_html,
    send_tenant_email,
)
from app.tenant_constants import DEFAULT_AGENCY_ID
from app.tenant_email_identity import build_agency_email_local_part, build_tenant_from_header


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
        mailgun_domain=overrides.get("mailgun_domain", delivery.mailgun_domain),
        api_key=overrides.get("api_key", delivery.api_key),
        api_provider=overrides.get("api_provider", delivery.api_provider),
    )


def _production_delivery(**overrides) -> EmailDeliverySettings:
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_PRODUCTION, mailgun_api_key="mg_live_test")
    )
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
        mailgun_domain=overrides.get("mailgun_domain", delivery.mailgun_domain),
        api_key=overrides.get("api_key", delivery.api_key),
        api_provider=overrides.get("api_provider", delivery.api_provider),
    )


def _send_kwargs(**overrides):
    base = {
        "agency_id": DEFAULT_AGENCY_ID,
        "user_id": "1",
        "agency_name": "Cruise Sea-kers Travel",
        "agent_email": "jane.agent@agency.com",
        "recipient": "client@example.com",
        "email_type": "research_proposal",
        "subject": "Cruise Proposal – Caribbean (2 options)",
        "html_content": "<p>Proposal body</p>",
        "travel_request_id": None,
    }
    base.update(overrides)
    return base


# --- tenant from header ---


def test_build_agency_email_local_part_strips_punctuation_and_hyphens():
    assert build_agency_email_local_part("Cruise Sea-kers Travel") == "CruiseSeakersTravelConcierge"


def test_build_agency_email_local_part_falls_back_for_empty_name():
    assert build_agency_email_local_part("   ") == "AgencyConcierge"


def test_build_tenant_from_header_formats_display_name_and_mailbox():
    formatted = build_tenant_from_header(
        agency_name="Cruise Sea-kers Travel",
        mail_domain="mail.sailspipeline.com",
    )

    display_name, mailbox = parseaddr(formatted)
    assert display_name == "Cruise Sea-kers Travel"
    assert mailbox == "CruiseSeakersTravelConcierge@mail.sailspipeline.com"


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
        branding=_sample_email_branding(agency_name="Cruise Seakers Travel LLC"),
        email_signature="<p>Best regards,<br/>Jane</p>",
    )

    assert "Cruise Seakers Travel LLC" in html
    assert "Best regards" in html
    assert BRAND_NAME in html


def test_render_email_logo_only_base_html_omits_advisor_header_and_centers_logo():
    html = render_email_logo_only_base_html(
        content="<p>Waiver body</p>",
        agent_name="jane.agent",
        branding=_sample_email_branding(
            agency_name="Cruise Seakers Travel LLC",
            brand_logo_absolute_url="https://cdn.example.com/logo.png",
        ),
    )

    header_html = html.split("<p>Waiver body</p>")[0]

    assert "Your travel advisor" not in html
    assert "jane.agent" not in header_html
    assert "text-align:center" in header_html
    assert "https://cdn.example.com/logo.png" in header_html
    assert "<p>Waiver body</p>" in html


# --- Environment toggles ---


def test_development_settings_default_to_mailpit_smtp():
    delivery = resolve_email_delivery_settings(
        Settings(
            app_env=APP_ENV_DEVELOPMENT,
            email_backend="api",
            email_host="smtp.sendgrid.net",
            email_port=587,
            mailgun_api_key="live-secret",
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
        Settings(app_env=APP_ENV_DEVELOPMENT, mailgun_api_key="must-be-ignored"),
    )
    service = EmailDeliveryService(SimpleNamespace())

    assert service._delivery.backend == "smtp"
    assert service._delivery.smtp_host == DEVELOPMENT_MAILPIT_HOST


def test_development_init_rejects_api_backend_override():
    delivery = _development_delivery(backend="api")

    with pytest.raises(DevelopmentEmailIsolationError, match="requires SMTP transport"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


def test_development_init_rejects_loaded_api_credentials():
    delivery = _development_delivery(api_key="mg_live_secret")

    with pytest.raises(DevelopmentEmailIsolationError, match="forbids loading cloud email API credentials"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


def test_development_init_rejects_non_local_smtp_host():
    delivery = _development_delivery(smtp_host="smtp.sendgrid.net")

    with pytest.raises(DevelopmentEmailIsolationError, match="is not allowed"):
        EmailDeliveryService(SimpleNamespace(), delivery_settings=delivery)


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_send_tenant_email_smtp_sets_from_and_reply_to(mock_send):
    mock_send.return_value = {}
    delivery = _development_delivery()

    asyncio.run(
        send_tenant_email(
            agency_name="Cruise Sea-kers Travel",
            agent_email="jane.agent@agency.com",
            recipient_email="client@example.com",
            subject="Your cruise proposal",
            html_content="<p>Hello</p>",
            delivery_settings=delivery,
        )
    )

    message = mock_send.await_args.args[0]
    display_name, from_address = parseaddr(message["From"])
    assert display_name == "Cruise Sea-kers Travel"
    assert from_address == "CruiseSeakersTravelConcierge@mail.sailspipeline.com"
    assert message["Reply-To"] == "jane.agent@agency.com"
    assert message["To"] == "client@example.com"
    assert message["Subject"] == "Your cruise proposal"


@patch("app.services.email_service.requests.post")
def test_send_tenant_email_production_uses_mailgun(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
    delivery = _production_delivery()

    asyncio.run(
        send_tenant_email(
            agency_name="Cruise Sea-kers Travel",
            agent_email="jane.agent@agency.com",
            recipient_email="client@example.com",
            subject="Your cruise proposal",
            html_content="<p>Hello</p>",
            delivery_settings=delivery,
        )
    )

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["auth"] == ("api", "mg_live_test")
    assert call_kwargs["data"]["to"] == "client@example.com"
    assert call_kwargs["data"]["h:Reply-To"] == "jane.agent@agency.com"
    assert "CruiseSeakersTravelConcierge@mail.sailspipeline.com" in call_kwargs["data"]["from"]
    assert call_kwargs["data"]["subject"] == "Your cruise proposal"
    assert call_kwargs["data"]["html"] == "<p>Hello</p>"


def test_development_blocks_external_api_calls():
    delivery = _development_delivery(backend="api", api_key="mg_test")

    with pytest.raises(DevelopmentEmailIsolationError, match="blocked when APP_ENV=development"):
        asyncio.run(
            send_tenant_email(
                agency_name="Cruise Sea-kers Travel",
                agent_email="agent@example.com",
                recipient_email="client@example.com",
                subject="Test",
                html_content="<p>Hi</p>",
                delivery_settings=delivery,
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
        Settings(app_env=APP_ENV_STAGING, mailgun_api_key_staging="mg_staging_test")
    )

    assert delivery.backend == "api"
    assert delivery.api_key == "mg_staging_test"


def test_production_resolves_to_api_backend():
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_PRODUCTION, mailgun_api_key="mg_live_production")
    )

    assert delivery.backend == "api"
    assert delivery.api_key == "mg_live_production"


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


@patch("app.services.email_service.requests.post")
def test_staging_api_failure_writes_failed_audit_log(mock_post, db, test_user):
    mock_post.side_effect = RuntimeError("Mailgun timeout")
    delivery = resolve_email_delivery_settings(
        Settings(app_env=APP_ENV_STAGING, mailgun_api_key_staging="mg_staging_test")
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
    assert "Mailgun timeout" in (log.error_message or "")


@patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock)
def test_audit_log_truncates_long_error_messages(mock_send, db, test_user):
    mock_send.side_effect = RuntimeError("x" * 5000)
    service = EmailDeliveryService(db, delivery_settings=_development_delivery())

    asyncio.run(service.send_transactional_email(**_send_kwargs(user_id=str(test_user.id))))

    log = db.query(AgencyEmailLog).order_by(AgencyEmailLog.created_at.desc()).first()
    assert log is not None
    assert log.status == EMAIL_STATUS_FAILED
    assert len(log.error_message or "") == 4000
