from __future__ import annotations

from html import escape

from sqlalchemy.orm import Session

from app.agency_email_branding import (
    AgencyEmailBranding,
    render_email_cta_button,
    render_platform_compliance_footer,
)
from app.branding import BRAND_APP_TITLE, BRAND_NAME
from app.config import settings
from app.models import Agency, User
from app.services.agency_settings_service import DEFAULT_PRIMARY_COLOR, DEFAULT_SECONDARY_COLOR
from app.services.email_service import EmailDeliveryService

WELCOME_EMAIL_TYPE = "tenant_welcome"


def load_system_welcome_branding() -> AgencyEmailBranding:
    """Default SailsPipeline branding for platform onboarding emails."""
    return AgencyEmailBranding(
        agency_id="system",
        agency_name=BRAND_NAME,
        brand_logo_url="/sailspipeline-logo.png",
        brand_logo_absolute_url=f"{settings.public_app_base_url.rstrip('/')}/sailspipeline-logo.png",
        primary_color=DEFAULT_PRIMARY_COLOR,
        secondary_color=DEFAULT_SECONDARY_COLOR,
        primary_text_color="#ffffff",
        email_signature_block=None,
    )


def build_welcome_email_content(
    *,
    admin_name: str,
    agency_name: str,
    organization_handle: str,
    username: str,
) -> str:
    safe_name = escape(admin_name.strip() or "there")
    safe_agency = escape(agency_name.strip())
    safe_handle = escape(organization_handle.strip())
    safe_username = escape(username.strip())
    login_url = escape(f"{settings.public_app_base_url.rstrip('/')}/", quote=True)
    branding = load_system_welcome_branding()

    cta = render_email_cta_button(
        href=f"{settings.public_app_base_url.rstrip('/')}/",
        label="Open your dashboard",
        primary_color=branding.primary_color,
        text_color=branding.primary_text_color,
    )

    return f"""
<p style="margin:0 0 18px;font-size:22px;font-weight:700;line-height:1.35;color:#102a43;">
  Welcome to {escape(BRAND_NAME)}
</p>
<p style="margin:0 0 16px;">
  Hi {safe_name},
</p>
<p style="margin:0 0 16px;">
  Your travel agency workspace for <strong>{safe_agency}</strong> is live.
  {BRAND_APP_TITLE} is ready for client intake, proposals, communications, and compliance
  workflows — all in one branded workspace.
</p>
<p style="margin:0 0 16px;">
  We created your owner account using a <strong>firstname.lastname</strong> username derived from
  the name you provided. Save these sign-in details:
</p>
<ul style="margin:0 0 24px;padding-left:1.25rem;line-height:1.7;color:#243b53;">
  <li>Organization handle: <strong>{safe_handle}</strong></li>
  <li>Username: <strong>{safe_username}</strong></li>
  <li>Password: the password you chose during registration</li>
</ul>
<p style="margin:0 0 28px;text-align:center;">
  {cta}
</p>
<p style="margin:0;font-size:14px;line-height:1.6;color:#486581;">
  Bookmark your sign-in page: <a href="{login_url}" style="color:#0b7285;">{login_url}</a>
</p>
""".strip()


def render_welcome_email_html(
    *,
    admin_name: str,
    agency_name: str,
    organization_handle: str,
    username: str,
) -> str:
    branding = load_system_welcome_branding()
    content = build_welcome_email_content(
        admin_name=admin_name,
        agency_name=agency_name,
        organization_handle=organization_handle,
        username=username,
    )
    from pathlib import Path

    template_path = Path(__file__).resolve().parent.parent / "templates" / "email_base.html"
    template = template_path.read_text(encoding="utf-8")
    preview_text = f"Welcome to {BRAND_NAME} — your {agency_name.strip()} workspace is ready."

    return (
        template.replace("{{ page_title }}", escape(f"Welcome to {BRAND_NAME}"))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace("{{ agency_header }}", render_system_welcome_header_html(branding))
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", "")
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=BRAND_NAME,
                agency_name=agency_name.strip(),
            ),
        )
    )


def render_system_welcome_header_html(branding: AgencyEmailBranding) -> str:
    safe_platform = escape(BRAND_NAME)
    safe_primary = escape(branding.primary_color)
    safe_secondary = escape(branding.secondary_color)

    if branding.brand_logo_absolute_url:
        safe_logo = escape(branding.brand_logo_absolute_url, quote=True)
        brand_markup = (
            f'<img src="{safe_logo}" alt="{safe_platform}" width="220" '
            f'style="display:block;margin:0 auto;max-width:220px;width:100%;height:auto;border:0;" />'
        )
    else:
        brand_markup = (
            f'<div style="font-size:26px;font-weight:700;line-height:1.25;color:{safe_primary};'
            f'text-align:center;">{safe_platform}</div>'
        )

    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td class="email-header-cell"
      style="padding:32px 32px 24px;background:linear-gradient(180deg,#f8fbff 0%,#eef4fa 100%);
        border-bottom:2px solid {safe_primary};text-align:center;">
      {brand_markup}
      <div style="margin-top:16px;font-size:12px;font-weight:700;letter-spacing:0.14em;
        text-transform:uppercase;color:{safe_secondary};">Workspace provisioned</div>
    </td>
  </tr>
</table>
""".strip()


async def dispatch_tenant_welcome_email(
    db: Session,
    *,
    user: User,
    agency: Agency,
    admin_name: str,
) -> bool:
    subject = f"Welcome to {BRAND_NAME} — {agency.name} is ready"
    html_content = render_welcome_email_html(
        admin_name=admin_name,
        agency_name=agency.name,
        organization_handle=agency.organization_handle,
        username=user.username,
    )
    mailer = EmailDeliveryService(db)
    return await mailer.send_transactional_email(
        agency_id=agency.id,
        user_id=str(user.id),
        user_name=BRAND_NAME,
        user_email=user.email,
        recipient=user.email,
        email_type=WELCOME_EMAIL_TYPE,
        subject=subject,
        html_content=html_content,
    )
