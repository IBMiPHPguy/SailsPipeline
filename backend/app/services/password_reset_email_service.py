from __future__ import annotations

from html import escape
from pathlib import Path

from sqlalchemy.orm import Session

from app.agency_email_branding import (
    AgencyEmailBranding,
    load_agency_email_branding,
    render_email_cta_button,
    render_platform_compliance_footer,
)
from app.branding import BRAND_APP_TITLE
from app.config import settings
from app.models import User
from app.services.email_service import EmailDeliveryService
from app.services.welcome_email_service import load_system_welcome_branding

PASSWORD_RESET_EMAIL_TYPE = "password_reset"
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_base.html"


def resolve_password_reset_branding(db: Session, user: User) -> AgencyEmailBranding:
    if user.agency_id:
        return load_agency_email_branding(db, agency_id=user.agency_id)
    return load_system_welcome_branding()


def render_password_reset_header_html(branding: AgencyEmailBranding) -> str:
    safe_agency = escape(branding.agency_name)
    safe_platform = escape(BRAND_APP_TITLE)
    safe_primary = escape(branding.primary_color)
    safe_secondary = escape(branding.secondary_color)

    if branding.brand_logo_absolute_url:
        safe_logo = escape(branding.brand_logo_absolute_url, quote=True)
        brand_markup = (
            f'<img src="{safe_logo}" alt="{safe_agency}" width="200" '
            f'style="display:block;margin:0 auto;max-width:200px;width:100%;height:auto;border:0;" />'
        )
    else:
        brand_markup = (
            f'<div style="font-size:24px;font-weight:700;line-height:1.25;color:{safe_primary};'
            f'text-align:center;">{safe_agency}</div>'
        )

    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td class="email-header-cell"
      style="padding:32px 32px 24px;background:linear-gradient(180deg,#f8fbff 0%,#eef4fa 100%);
        border-bottom:2px solid {safe_primary};text-align:center;">
      {brand_markup}
      <div style="margin-top:16px;font-size:12px;font-weight:700;letter-spacing:0.14em;
        text-transform:uppercase;color:{safe_secondary};">Password recovery</div>
      <div style="margin-top:8px;font-size:13px;line-height:1.5;color:#627d98;">
        Powered by {safe_platform}
      </div>
    </td>
  </tr>
</table>
""".strip()


def build_password_reset_email_content(
    *,
    branding: AgencyEmailBranding,
    reset_url: str,
    organization_handle: str,
) -> str:
    safe_url = escape(reset_url, quote=True)
    safe_handle = escape(organization_handle.strip())
    safe_agency = escape(branding.agency_name)
    safe_primary = escape(branding.primary_color)
    cta = render_email_cta_button(
        href=reset_url,
        label="Reset your password",
        primary_color=branding.primary_color,
        text_color=branding.primary_text_color,
    )

    return f"""
<p style="margin:0 0 18px;font-size:22px;font-weight:700;line-height:1.35;color:#102a43;text-align:center;">
  Password reset request
</p>
<p style="margin:0 0 16px;">
  We received a request to reset the password for your account at <strong>{safe_agency}</strong>
  (organization handle: <strong>{safe_handle}</strong>).
  Click the button below to choose a new password. This link expires in one hour.
</p>
<p style="margin:0 0 28px;text-align:center;">
  {cta}
</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#486581;">
  If you did not request a password reset, you can safely ignore this email. Your password will
  remain unchanged.
</p>
<p style="margin:16px 0 0;font-size:13px;line-height:1.5;color:#829ab1;word-break:break-all;">
  Button not working? Copy and paste this link into your browser:<br />
  <a href="{safe_url}" style="color:{safe_primary};">{safe_url}</a>
</p>
""".strip()


def render_password_reset_email_html(
    *,
    branding: AgencyEmailBranding,
    reset_url: str,
    organization_handle: str,
) -> str:
    content = build_password_reset_email_content(
        branding=branding,
        reset_url=reset_url,
        organization_handle=organization_handle,
    )
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    preview_text = f"Reset your {branding.agency_name} password — link expires in one hour."

    return (
        template.replace("{{ page_title }}", escape(f"Password Reset — {branding.agency_name}"))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace("{{ agency_header }}", render_password_reset_header_html(branding))
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", "")
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=branding.agency_name,
                agency_name=branding.agency_name,
            ),
        )
    )


async def dispatch_password_reset_email(
    db: Session,
    *,
    user: User,
    raw_token: str,
    organization_handle: str,
) -> bool:
    branding = resolve_password_reset_branding(db, user)
    reset_url = (
        f"{settings.public_app_base_url.rstrip('/')}/reset-password"
        f"?token={raw_token}"
    )
    subject = f"Password reset — {branding.agency_name}"
    html_content = render_password_reset_email_html(
        branding=branding,
        reset_url=reset_url,
        organization_handle=organization_handle,
    )
    mailer = EmailDeliveryService(db)
    agency_id = user.agency_id or "system"
    return await mailer.send_transactional_email(
        agency_id=agency_id,
        user_id=str(user.id),
        user_name=branding.agency_name,
        user_email=user.email,
        recipient=user.email,
        email_type=PASSWORD_RESET_EMAIL_TYPE,
        subject=subject,
        html_content=html_content,
    )
