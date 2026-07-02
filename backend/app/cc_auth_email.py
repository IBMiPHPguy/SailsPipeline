from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape

from app.branding import BRAND_NAME
from app.cc_auth_helpers import CcAuthCruiseSummary

CC_AUTH_CONTENT_START = "<!-- sailspipeline-cc-auth-content-start -->"
CC_AUTH_CONTENT_END = "<!-- sailspipeline-cc-auth-content-end -->"


def _format_money(value: Decimal | float | str | int) -> str:
    amount = Decimal(str(value))
    return f"${amount:,.2f}"


def _format_display_date(value: date) -> str:
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def build_cc_auth_email_html(
    *,
    passenger_name: str,
    cruises: list[CcAuthCruiseSummary],
    total_deposit_due: Decimal,
    portal_url: str,
) -> str:
    cruise_blocks: list[str] = []
    for index, cruise in enumerate(cruises, start=1):
        cruise_blocks.append(
            f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
              style="margin:0 0 20px;border:1px solid #d9e2ec;border-radius:12px;overflow:hidden;background:#ffffff;">
              <tr>
                <td style="padding:14px 18px;background:linear-gradient(135deg,#102a43 0%,#243b53 100%);color:#ffffff;">
                  <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.85;">
                    Sailing {index}
                  </div>
                  <div style="margin-top:4px;font-size:18px;font-weight:700;line-height:1.3;">
                    {escape(cruise.cruise_line)} · {escape(cruise.ship)}
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:18px;">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                    <tr>
                      <td width="50%" valign="top" style="padding:0 10px 12px 0;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">
                          Sailing date
                        </div>
                        <div style="margin-top:4px;font-size:15px;color:#102a43;">
                          {_format_display_date(cruise.sailing_date)}
                        </div>
                      </td>
                      <td width="50%" valign="top" style="padding:0 0 12px 10px;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">
                          Cabin type
                        </div>
                        <div style="margin-top:4px;font-size:15px;color:#102a43;">
                          {escape(cruise.cabin_type)}
                        </div>
                      </td>
                    </tr>
                    <tr>
                      <td width="50%" valign="top" style="padding:0 10px 0 0;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">
                          Deposit amount due
                        </div>
                        <div style="margin-top:4px;font-size:15px;color:#102a43;font-weight:600;">
                          {_format_money(cruise.deposit_amount)}
                        </div>
                      </td>
                      <td width="50%" valign="top" style="padding:0;">
                        <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">
                          Final payment due
                        </div>
                        <div style="margin-top:4px;font-size:15px;color:#102a43;">
                          {_format_display_date(cruise.final_payment_due_date)}
                        </div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
            """
        )

    cruise_html = "".join(cruise_blocks)
    safe_passenger = escape(passenger_name.strip())
    safe_portal_url = escape(portal_url, quote=True)

    inner = f"""
    {CC_AUTH_CONTENT_START}
    <p style="margin:0 0 16px;font-size:16px;line-height:1.65;color:#243b53;">
      Dear {safe_passenger},
    </p>
    <p style="margin:0 0 20px;font-size:16px;line-height:1.65;color:#243b53;">
      Your travel advisor has requested a secure credit card authorization to hold your upcoming
      sailing reservation with {BRAND_NAME}. Please review the details below and complete
      authorization at your earliest convenience.
    </p>

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
      style="margin:0 0 24px;border:1px solid #c6f6d5;border-radius:12px;background:#f0fff4;">
      <tr>
        <td style="padding:16px 18px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#276749;">
            Total deposit amount due
          </div>
          <div style="margin-top:6px;font-size:28px;font-weight:700;color:#102a43;line-height:1.2;">
            {_format_money(total_deposit_due)}
          </div>
          <div style="margin-top:6px;font-size:14px;color:#486581;">
            Combined deposits for all rooms across your accepted sailing
            {"s" if len(cruises) != 1 else ""}.
          </div>
        </td>
      </tr>
    </table>

    {cruise_html}

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:28px 0 24px;">
      <tr>
        <td align="center">
          <a href="{safe_portal_url}"
            style="display:inline-block;padding:16px 32px;background:#0b7285;color:#ffffff;
              font-size:16px;font-weight:700;text-decoration:none;border-radius:10px;
              box-shadow:0 4px 14px rgba(11,114,133,0.35);letter-spacing:0.02em;">
            Securely Authorize Card
          </a>
        </td>
      </tr>
    </table>

    <p style="margin:0;font-size:13px;line-height:1.6;color:#829ab1;text-align:center;">
      For your security, this authorization link is encrypted and will expire in 48 hours.
    </p>
    {CC_AUTH_CONTENT_END}
    """

    return inner.strip()
