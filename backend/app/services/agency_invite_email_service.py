from __future__ import annotations

from html import escape
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.agency_email_branding import (
    AgencyEmailBranding,
    load_agency_email_branding,
    render_email_brand_header_html,
    render_email_cta_button,
    render_platform_compliance_footer,
)
from app.branding import BRAND_APP_TITLE, BRAND_NAME
from app.config import settings
from app.models import Agency, AgencyInvitation, User
from app.services.email_service import EmailDeliveryService
from app.tenant_roles import USER_ROLE_TENANT_AGENT, USER_ROLE_TENANT_SUPER_USER

AGENCY_INVITE_EMAIL_TYPE = "agency_team_invite"
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_base.html"

_ROLE_LABELS = {
    USER_ROLE_TENANT_AGENT: "Travel agent",
    USER_ROLE_TENANT_SUPER_USER: "Agency owner",
}


def _role_label(role: str) -> str:
    return _ROLE_LABELS.get(role, "Team member")


def build_agency_invite_email_content(
    *,
    branding: AgencyEmailBranding,
    agency: Agency,
    inviting_user: User,
    invitation: AgencyInvitation,
    invite_url: str,
) -> str:
    safe_agency = escape(branding.agency_name)
    safe_handle = escape((agency.organization_handle or "").strip())
    safe_inviter = escape(inviting_user.username.strip() or inviting_user.email)
    safe_role = escape(_role_label(invitation.role))
    safe_url = escape(invite_url, quote=True)
    safe_primary = escape(branding.primary_color)

    cta = render_email_cta_button(
        href=invite_url,
        label="Accept invitation",
        primary_color=branding.primary_color,
        text_color=branding.primary_text_color,
    )

    return f"""
<p style="margin:0 0 18px;font-size:22px;font-weight:700;line-height:1.35;color:#102a43;text-align:center;">
  You are invited to join {safe_agency}
</p>
<p style="margin:0 0 16px;">
  <strong>{safe_inviter}</strong> invited you to join <strong>{safe_agency}</strong> on
  {escape(BRAND_APP_TITLE)} as a <strong>{safe_role}</strong>.
</p>
<p style="margin:0 0 16px;">
  Use the button below to create your account. This invitation expires on
  <strong>{escape(invitation.expires_at.strftime("%Y-%m-%d %H:%M UTC"))}</strong>.
</p>
<ul style="margin:0 0 24px;padding-left:1.25rem;line-height:1.7;color:#243b53;">
  <li>Organization handle: <strong>{safe_handle}</strong></li>
  <li>Invited email: <strong>{escape(invitation.invite_email)}</strong></li>
</ul>
<p style="margin:0 0 28px;text-align:center;">
  {cta}
</p>
<p style="margin:0;font-size:13px;line-height:1.5;color:#829ab1;word-break:break-all;">
  Button not working? Copy and paste this link into your browser:<br />
  <a href="{safe_url}" style="color:{safe_primary};">{safe_url}</a>
</p>
""".strip()


def render_agency_invite_email_html(
    *,
    branding: AgencyEmailBranding,
    agency: Agency,
    inviting_user: User,
    invitation: AgencyInvitation,
    invite_url: str,
) -> str:
    content = build_agency_invite_email_content(
        branding=branding,
        agency=agency,
        inviting_user=inviting_user,
        invitation=invitation,
        invite_url=invite_url,
    )
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    preview_text = f"{inviting_user.username} invited you to join {branding.agency_name}."

    return (
        template.replace("{{ page_title }}", escape(f"Team invitation — {branding.agency_name}"))
        .replace("{{ preview_text }}", escape(preview_text))
        .replace(
            "{{ agency_header }}",
            render_email_brand_header_html(branding, agent_name=inviting_user.username),
        )
        .replace("{{ content }}", content)
        .replace("{{ email_signature }}", "")
        .replace(
            "{{ platform_footer }}",
            render_platform_compliance_footer(
                agent_name=inviting_user.username,
                agency_name=branding.agency_name,
            ),
        )
    )


async def dispatch_agency_invite_email(
    db: Session,
    *,
    agency: Agency,
    inviting_user: User,
    invitation: AgencyInvitation,
) -> None:
    branding = load_agency_email_branding(db, agency_id=agency.id)
    invite_url = f"{settings.public_app_base_url.rstrip('/')}/register-agent?token={invitation.token}"
    subject = f"Join {branding.agency_name} on {BRAND_NAME}"
    html_content = render_agency_invite_email_html(
        branding=branding,
        agency=agency,
        inviting_user=inviting_user,
        invitation=invitation,
        invite_url=invite_url,
    )

    mailer = EmailDeliveryService(db)
    success = await mailer.send_transactional_email(
        agency_id=agency.id,
        user_id=str(inviting_user.id),
        agency_name=branding.agency_name,
        agent_email=inviting_user.email,
        recipient=invitation.invite_email,
        email_type=AGENCY_INVITE_EMAIL_TYPE,
        subject=subject,
        html_content=html_content,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Team invitation email could not be delivered. Check agency email logs.",
        )
