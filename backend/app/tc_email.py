from __future__ import annotations

from html import escape

from app.branding import BRAND_NAME

TC_CONTENT_START = "<!-- sailspipeline-master-terms-content-start -->"
TC_CONTENT_END = "<!-- sailspipeline-master-terms-content-end -->"


def build_master_terms_email_html(
    *,
    passenger_name: str,
    agency_name: str,
    portal_url: str,
) -> str:
    safe_name = escape(passenger_name)
    safe_agency = escape(agency_name)
    safe_url = escape(portal_url, quote=True)

    return f"""{TC_CONTENT_START}
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"
  style="font-family:Arial,Helvetica,sans-serif;color:#102a43;">
  <tr>
    <td style="padding:0 0 18px;">
      <p style="margin:0 0 14px;font-size:16px;line-height:1.6;">
        Hello <strong>{safe_name}</strong>,
      </p>
      <p style="margin:0 0 14px;font-size:16px;line-height:1.6;">
        Before we finalize your cruise booking, {safe_agency} needs you to review and accept our
        Master Terms &amp; Conditions. This is a one-time acceptance that stays on file for all future
        bookings with us.
      </p>
      <p style="margin:0 0 22px;font-size:16px;line-height:1.6;">
        Please use the secure button below to open your personal review portal. The link expires in 48 hours.
      </p>
    </td>
  </tr>
  <tr>
    <td align="center" style="padding:0 0 24px;">
      <a href="{safe_url}"
        style="display:inline-block;padding:14px 28px;background:#0b7285;color:#ffffff;text-decoration:none;
          border-radius:8px;font-size:16px;font-weight:700;">
        Review &amp; Accept Master Terms
      </a>
    </td>
  </tr>
  <tr>
    <td style="padding:0;">
      <p style="margin:0;font-size:13px;line-height:1.6;color:#627d98;">
        If the button does not work, copy and paste this link into your browser:<br />
        <a href="{safe_url}" style="color:#0b7285;word-break:break-all;">{safe_url}</a>
      </p>
      <p style="margin:16px 0 0;font-size:13px;line-height:1.6;color:#627d98;">
        Sent securely via {escape(BRAND_NAME)}.
      </p>
    </td>
  </tr>
</table>
{TC_CONTENT_END}"""
