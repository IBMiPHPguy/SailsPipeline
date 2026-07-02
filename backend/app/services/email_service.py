from __future__ import annotations

import logging
import re
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape
from pathlib import Path

import aiosmtplib
from sqlalchemy.orm import Session

from app.branding import BRAND_NAME
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


def render_email_base_html(*, content: str, agent_name: str, agency_name: str) -> str:
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return (
        template.replace("{{ content }}", content)
        .replace("{{ agent_name }}", escape(agent_name))
        .replace("{{ agency_name }}", escape(agency_name))
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

    def _block_external_email_api(self) -> None:
        if self._delivery.environment in {"development", "test"}:
            raise DevelopmentEmailIsolationError(
                "External email provider API calls are blocked when APP_ENV=development. "
                "Local testing must route through Mailpit SMTP only."
            )

    async def send_transactional_email(
        self,
        agency_id: str,
        user_id: str,
        user_name: str,
        user_email: str,
        recipient: str,
        email_type: str,
        subject: str,
        html_content: str,
        travel_request_id: str | None = None,
    ) -> bool:
        status = EMAIL_STATUS_SENT
        error_message: str | None = None
        success = False

        try:
            if self._delivery.backend == "api":
                await self._send_via_api(
                    recipient=recipient,
                    subject=subject,
                    html_content=html_content,
                    user_name=user_name,
                    user_email=user_email,
                )
            else:
                await self._send_via_smtp(
                    recipient=recipient,
                    subject=subject,
                    html_content=html_content,
                    user_name=user_name,
                    user_email=user_email,
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

    async def _send_via_smtp(
        self,
        *,
        recipient: str,
        subject: str,
        html_content: str,
        user_name: str,
        user_email: str,
    ) -> None:
        hostname = self._delivery.smtp_host
        if self._delivery.environment in {"development", "test"}:
            if hostname not in ALLOWED_DEVELOPMENT_SMTP_HOSTS:
                raise DevelopmentEmailIsolationError(
                    f"Refusing to open SMTP connection to non-local host '{hostname}' in development."
                )

        message = self._build_message(
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            user_name=user_name,
            user_email=user_email,
        )
        await aiosmtplib.send(
            message,
            hostname=hostname,
            port=self._delivery.smtp_port,
            username=self._delivery.smtp_username or None,
            password=self._delivery.smtp_password or None,
            start_tls=self._delivery.smtp_use_tls,
        )

    async def _send_via_api(
        self,
        *,
        recipient: str,
        subject: str,
        html_content: str,
        user_name: str,
        user_email: str,
    ) -> None:
        self._block_external_email_api()

        if not self._delivery.api_key:
            raise RuntimeError(
                f"Email API key missing for APP_ENV={self._delivery.environment}. "
                "Configure the tier-appropriate provider credential."
            )

        if self._delivery.environment == APP_ENV_STAGING:
            # STAGING SANDBOX TIER: wire Resend/Postmark sandbox credentials here.
            # Use EMAIL_API_KEY_STAGING and optional EMAIL_FROM_ADDRESS_STAGING.
            logger.info(
                "Staging email dispatch via %s (sandbox) to %s",
                self._delivery.api_provider,
                recipient,
            )
        else:
            logger.info(
                "Production email dispatch via %s to %s",
                self._delivery.api_provider,
                recipient,
            )

        # Provider SDK placeholder (Resend / Postmark):
        #
        #   response = await provider_client.emails.send({
        #       "from": self._format_from_header(user_name),
        #       "to": [recipient],
        #       "subject": subject,
        #       "html": html_content,
        #       "reply_to": user_email,
        #   })
        _ = recipient, subject, html_content, user_name, user_email
        raise NotImplementedError(
            f"APP_ENV={self._delivery.environment} routes through the {self._delivery.api_provider} API, "
            "but the provider SDK is not wired yet."
        )

    def _build_message(
        self,
        *,
        recipient: str,
        subject: str,
        html_content: str,
        user_name: str,
        user_email: str,
    ) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["From"] = self._format_from_header(user_name)
        message["Sender"] = self._delivery.from_address
        message["Reply-To"] = user_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html", "utf-8"))
        return message

    def _format_from_header(self, user_name: str) -> str:
        display_name = f"{user_name.strip()} via {BRAND_NAME}"
        return formataddr((display_name, self._delivery.from_address))

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
