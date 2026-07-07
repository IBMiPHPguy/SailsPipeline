from __future__ import annotations

import asyncio
import logging
import re
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape
from pathlib import Path

import aiosmtplib
import requests
from sqlalchemy.orm import Session

from app.agency_email_branding import (
    AgencyEmailBranding,
    render_email_brand_header_html,
    render_email_logo_only_header_html,
    render_email_signature_section,
    render_platform_compliance_footer,
)
from app.email_config import (
    ALLOWED_DEVELOPMENT_SMTP_HOSTS,
    APP_ENV_STAGING,
    DevelopmentEmailIsolationError,
    EmailDeliverySettings,
)
from app.models import AgencyEmailLog
from app.research_proposal_email import (
    RESEARCH_PROPOSAL_CONTENT_END,
    RESEARCH_PROPOSAL_CONTENT_START,
)
from app.tenant_email_identity import build_tenant_from_header

logger = logging.getLogger(__name__)

EMAIL_STATUS_SENT = "sent"
EMAIL_STATUS_FAILED = "failed"

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_base.html"


def extract_communication_html_content(body: str) -> str:
    """Return inner message HTML when the draft is already a full document."""
    stripped = body.strip()

    start = stripped.find(RESEARCH_PROPOSAL_CONTENT_START)
    end = stripped.find(RESEARCH_PROPOSAL_CONTENT_END)
    if start != -1 and end != -1 and end > start:
        return stripped[start + len(RESEARCH_PROPOSAL_CONTENT_START) : end].strip()

    if not stripped.lower().startswith("<!doctype") and not stripped.lower().startswith("<html"):
        return stripped

    # Match the outer proposal body cell, not nested option tables inside it.
    match = re.search(
        r'<td style="padding:28px;">\s*(.*?)\s*</td>\s*</tr>\s*</table>\s*</td>\s*</tr>\s*</table>',
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    body_match = re.search(r"<body[^>]*>(.*)</body>", stripped, flags=re.DOTALL | re.IGNORECASE)
    if body_match:
        return body_match.group(1).strip()

    return stripped


def render_email_base_html(*, content: str, agent_name: str, branding: AgencyEmailBranding) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    preview_text = f"Message from {agent_name} at {branding.agency_name}."
    return (
        template.replace("{{ page_title }}", escape(branding.agency_name))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace(
            "{{ agency_header }}",
            render_email_brand_header_html(branding, agent_name=agent_name),
        )
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", render_email_signature_section(branding.email_signature_block))
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=agent_name,
                agency_name=branding.agency_name,
            ),
        )
    )


def render_email_logo_only_base_html(*, content: str, agent_name: str, branding: AgencyEmailBranding) -> str:
    """Wrap email content with a centered logo header (no advisor name or agency name band)."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    preview_text = f"Message from {branding.agency_name}."
    return (
        template.replace("{{ page_title }}", escape(branding.agency_name))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace("{{ agency_header }}", render_email_logo_only_header_html(branding))
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", render_email_signature_section(branding.email_signature_block))
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=agent_name,
                agency_name=branding.agency_name,
            ),
        )
    )


def _dispatch_mailgun_message(
    *,
    api_key: str,
    mailgun_domain: str,
    from_header: str,
    recipient_email: str,
    subject: str,
    html_content: str,
    agent_email: str,
) -> None:
    response = requests.post(
        f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
        auth=("api", api_key),
        data={
            "from": from_header,
            "to": recipient_email,
            "subject": subject,
            "html": html_content,
            "h:Reply-To": agent_email,
        },
        timeout=30,
    )
    response.raise_for_status()


async def send_tenant_email(
    *,
    agency_name: str,
    agent_email: str,
    recipient_email: str,
    subject: str,
    html_content: str,
    delivery_settings: EmailDeliverySettings,
) -> None:
    """Send a tenant-branded HTML email via Mailpit SMTP (dev) or Mailgun REST API (production)."""
    from_header = build_tenant_from_header(
        agency_name=agency_name,
        mail_domain=delivery_settings.mailgun_domain,
    )

    if delivery_settings.backend == "smtp":
        hostname = delivery_settings.smtp_host
        if delivery_settings.environment in {"development", "test"}:
            if hostname not in ALLOWED_DEVELOPMENT_SMTP_HOSTS:
                raise DevelopmentEmailIsolationError(
                    f"Refusing to open SMTP connection to non-local host '{hostname}' in development."
                )

        message = MIMEMultipart("alternative")
        message["From"] = from_header
        message["Reply-To"] = agent_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html", "utf-8"))

        await aiosmtplib.send(
            message,
            hostname=hostname,
            port=delivery_settings.smtp_port,
            username=delivery_settings.smtp_username or None,
            password=delivery_settings.smtp_password or None,
            start_tls=delivery_settings.smtp_use_tls,
        )
        return

    if delivery_settings.environment in {"development", "test"}:
        raise DevelopmentEmailIsolationError(
            "External email provider API calls are blocked when APP_ENV=development. "
            "Local testing must route through Mailpit SMTP only."
        )

    if not delivery_settings.api_key:
        raise RuntimeError(
            f"Mailgun API key missing for APP_ENV={delivery_settings.environment}. "
            "Configure the tier-appropriate MAILGUN_API_KEY."
        )

    if delivery_settings.environment == APP_ENV_STAGING:
        logger.info("Staging email dispatch via Mailgun (sandbox) to %s", recipient_email)
    else:
        logger.info("Production email dispatch via Mailgun to %s", recipient_email)

    await asyncio.to_thread(
        _dispatch_mailgun_message,
        api_key=delivery_settings.api_key,
        mailgun_domain=delivery_settings.mailgun_domain,
        from_header=from_header,
        recipient_email=recipient_email,
        subject=subject,
        html_content=html_content,
        agent_email=agent_email,
    )


class EmailDeliveryService:
    """Environment-aware transactional email delivery with immutable audit logging."""

    def __init__(self, db: Session, *, delivery_settings: EmailDeliverySettings | None = None) -> None:
        from app.config import settings

        self.db = db
        self._delivery = delivery_settings or settings.resolve_email_delivery_settings()
        self._assert_development_isolation_contract()
        logger.info(
            "EmailDeliveryService configured for APP_ENV=%s using %s transport (%s)",
            self._delivery.environment,
            self._delivery.backend,
            self._delivery.smtp_host if self._delivery.backend == "smtp" else self._delivery.api_provider,
        )

    def _assert_development_isolation_contract(self) -> None:
        if self._delivery.environment not in {"development", "test"}:
            return

        if self._delivery.backend != "smtp":
            raise DevelopmentEmailIsolationError(
                "Development email isolation requires SMTP transport to local Mailpit."
            )

        if self._delivery.api_key:
            raise DevelopmentEmailIsolationError(
                "Development email isolation forbids loading cloud email API credentials."
            )

        if self._delivery.smtp_host not in ALLOWED_DEVELOPMENT_SMTP_HOSTS:
            raise DevelopmentEmailIsolationError(
                f"Development SMTP host '{self._delivery.smtp_host}' is not allowed. "
                f"Use one of: {', '.join(sorted(ALLOWED_DEVELOPMENT_SMTP_HOSTS))}."
            )

    async def send_transactional_email(
        self,
        agency_id: str,
        user_id: str,
        agency_name: str,
        agent_email: str,
        recipient: str,
        email_type: str,
        subject: str,
        html_content: str,
        travel_request_id: str | None = None,
    ) -> bool:
        """Send a tenant email and persist an immutable agency audit log entry."""
        status = EMAIL_STATUS_SENT
        error_message: str | None = None
        success = False

        try:
            await send_tenant_email(
                agency_name=agency_name,
                agent_email=agent_email,
                recipient_email=recipient,
                subject=subject,
                html_content=html_content,
                delivery_settings=self._delivery,
            )
            success = True
        except Exception as exc:
            status = EMAIL_STATUS_FAILED
            error_message = str(exc)[:4000]
        finally:
            self._write_audit_log(
                agency_id=agency_id,
                user_id=int(user_id),
                travel_request_id=int(travel_request_id) if travel_request_id else None,
                recipient_email=recipient,
                email_type=email_type,
                subject_line=subject,
                status=status,
                error_message=error_message,
            )

        return success

    def _write_audit_log(
        self,
        *,
        agency_id: str,
        user_id: int,
        travel_request_id: int | None,
        recipient_email: str,
        email_type: str,
        subject_line: str,
        status: str,
        error_message: str | None,
    ) -> None:
        log_entry = AgencyEmailLog(
            id=str(uuid.uuid4()),
            agency_id=agency_id,
            user_id=user_id,
            travel_request_id=travel_request_id,
            recipient_email=recipient_email,
            email_type=email_type,
            subject_line=subject_line[:255],
            status=status,
            error_message=error_message,
        )
        self.db.add(log_entry)
        self.db.commit()
