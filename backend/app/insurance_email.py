from __future__ import annotations

from html import escape

from app.agency_email_branding import render_email_cta_button

INSURANCE_WAIVER_CONTENT_START = "<!-- sailspipeline-insurance-waiver-content-start -->"
INSURANCE_WAIVER_CONTENT_END = "<!-- sailspipeline-insurance-waiver-content-end -->"


def build_insurance_waiver_email_html(
    *,
    passenger_name: str,
    agency_name: str,
    portal_url: str,
    primary_color: str,
    primary_text_color: str | None = None,
) -> str:
    safe_name = escape(passenger_name)
    safe_agency = escape(agency_name)
    safe_url = escape(portal_url, quote=True)
    safe_primary = escape(primary_color)
    cta = render_email_cta_button(
        href=portal_url,
        label="Review & Sign Insurance Waiver",
        primary_color=primary_color,
        text_color=primary_text_color,
    )

    return f"""{INSURANCE_WAIVER_CONTENT_START}
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"
  style="font-family:Arial,Helvetica,sans-serif;color:#102a43;">
  <tr>
    <td style="padding:0 0 18px;">
      <p style="margin:0 0 14px;font-size:16px;line-height:1.6;">
        Hello <strong>{safe_name}</strong>,
      </p>
      <p style="margin:0 0 14px;font-size:16px;line-height:1.6;">
        {safe_agency} needs you to review and electronically sign a
        <strong>Declination of Travel Protection and Liability Waiver</strong> because you have
        elected not to purchase trip insurance for your upcoming cruise.
      </p>
      <p style="margin:0 0 22px;font-size:16px;line-height:1.6;">
        Please use the secure button below to open your personal waiver portal. The link expires in 48 hours.
      </p>
    </td>
  </tr>
  <tr>
    <td align="center" style="padding:0 0 24px;">
      {cta}
    </td>
  </tr>
  <tr>
    <td style="padding:0;">
      <p style="margin:0;font-size:13px;line-height:1.6;color:#627d98;">
        If the button does not work, copy and paste this link into your browser:<br />
        <a href="{safe_url}" style="color:{safe_primary};word-break:break-all;">{safe_url}</a>
      </p>
    </td>
  </tr>
</table>
{INSURANCE_WAIVER_CONTENT_END}"""
