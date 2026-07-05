from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agency_email_branding import AgencyEmailBranding, render_email_cta_button, render_platform_compliance_footer
from app.branding import BRAND_APP_TITLE, BRAND_NAME
from app.config import settings
from app.models import PlatformInvitation, User
from app.services.email_service import EmailDeliveryService
from app.services.welcome_email_service import load_system_welcome_branding, render_system_welcome_header_html

PLATFORM_INVITE_EMAIL_TYPE = "platform_onboarding_invite"
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_base.html"


def _onboarding_branding(invitation: PlatformInvitation) -> AgencyEmailBranding:
    system = load_system_welcome_branding()
    return AgencyEmailBranding(
        agency_id=system.agency_id,
        agency_name=invitation.target_agency_name.strip(),
        brand_logo_url=system.brand_logo_url,
        brand_logo_absolute_url=system.brand_logo_absolute_url,
        primary_color=system.primary_color,
        secondary_color=system.secondary_color,
        primary_text_color=system.primary_text_color,
        email_signature_block=None,
    )


def build_platform_invite_email_content(
    *,
    branding: AgencyEmailBranding,
    invitation: PlatformInvitation,
    inviting_user: User,
    invite_url: str,
) -> str:
    safe_agency = escape(branding.agency_name)
    safe_handle = escape(invitation.target_organization_handle.strip())
    safe_inviter = escape(inviting_user.username.strip() or inviting_user.email)
    safe_url = escape(invite_url, quote=True)
    safe_primary = escape(branding.primary_color)

    cta = render_email_cta_button(
        href=invite_url,
        label="Start onboarding",
        primary_color=branding.primary_color,
        text_color=branding.primary_text_color,
    )

    return f"""
<p style="margin:0 0 18px;font-size:22px;font-weight:700;line-height:1.35;color:#102a43;text-align:center;">
  Your {escape(BRAND_NAME)} workspace is ready to provision
</p>
<p style="margin:0 0 16px;">
  <strong>{safe_inviter}</strong> invited you to launch <strong>{safe_agency}</strong> on
  {escape(BRAND_APP_TITLE)}.
</p>
<p style="margin:0 0 16px;">
  Use the button below to create your owner account and activate your agency workspace.
  This invitation expires on
  <strong>{escape(invitation.expires_at.strftime("%Y-%m-%d %H:%M UTC"))}</strong>.
</p>
<ul style="margin:0 0 24px;padding-left:1.25rem;line-height:1.7;color:#243b53;">
  <li>Agency name: <strong>{safe_agency}</strong></li>
  <li>Organization handle: <strong>{safe_handle}</strong></li>
  <li>Owner email: <strong>{escape(invitation.invite_email)}</strong></li>
</ul>
<p style="margin:0 0 28px;text-align:center;">
  {cta}
</p>
<p style="margin:0;font-size:13px;line-height:1.5;color:#829ab1;word-break:break-all;">
  Button not working? Copy and paste this link into your browser:<br />
  <a href="{safe_url}" style="color:{safe_primary};">{safe_url}</a>
</p>
""".strip()


def render_platform_invite_email_html(
    *,
    branding: AgencyEmailBranding,
    invitation: PlatformInvitation,
    inviting_user: User,
    invite_url: str,
) -> str:
    content = build_platform_invite_email_content(
        branding=branding,
        invitation=invitation,
        inviting_user=inviting_user,
        invite_url=invite_url,
    )
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    preview_text = f"Launch {branding.agency_name} on {BRAND_NAME}."

    return (
        template.replace("{{ page_title }}", escape(f"Onboarding invitation — {branding.agency_name}"))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace("{{ agency_header }}", render_system_welcome_header_html(branding))
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", "")
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=BRAND_NAME,
                agency_name=branding.agency_name,
            ),
        )
    )


async def dispatch_platform_invite_email(
    db: Session,
    *,
    inviting_user: User,
    invitation: PlatformInvitation,
) -> None:
    branding = _onboarding_branding(invitation)
    invite_url = f"{settings.public_app_base_url.rstrip('/')}/onboarding?token={invitation.token}"
    subject = f"Launch {branding.agency_name} on {BRAND_NAME}"
    html_content = render_platform_invite_email_html(
        branding=branding,
        invitation=invitation,
        inviting_user=inviting_user,
        invite_url=invite_url,
    )

    mailer = EmailDeliveryService(db)
    success = await mailer.send_transactional_email(
        agency_id="system",
        user_id=str(inviting_user.id),
        agency_name=branding.agency_name,
        agent_email=inviting_user.email,
        recipient=invitation.invite_email,
        email_type=PLATFORM_INVITE_EMAIL_TYPE,
        subject=subject,
        html_content=html_content,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Platform onboarding invitation email could not be delivered.",
        )
