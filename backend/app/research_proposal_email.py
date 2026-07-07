from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape
from typing import Any

from app.agency_email_branding import AgencyEmailBranding, render_email_brand_logo_img
from app.branding import BRAND_NAME
from app.models import ProposedCruise
from app.proposed_cruise_helpers import cabin_rooms_from_cruise
from app.schemas import ProposedCruiseRoom, RequestPassengerRead
from app.services.proposed_cruise_service import build_room_passengers_from_links

RESEARCH_PROPOSAL_CONTENT_START = "<!-- sailspipeline-email-content-start -->"
RESEARCH_PROPOSAL_CONTENT_END = "<!-- sailspipeline-email-content-end -->"


def _format_money(value: Decimal | float | str | int) -> str:
    amount = Decimal(str(value))
    return f"${amount:,.2f}"


def _format_display_date(value: date) -> str:
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def _includes_payload(includes: Any) -> dict[str, Any]:
    if includes is None:
        return {}
    if hasattr(includes, "model_dump"):
        return includes.model_dump(mode="json")
    if isinstance(includes, dict):
        return includes
    return {}


def _format_includes(includes: dict[str, Any] | None) -> list[str]:
    payload = includes or {}
    lines: list[str] = []

    drink = payload.get("drink_package") or {}
    if drink.get("included"):
        name = (drink.get("name") or "").strip()
        lines.append(f"Drink package{f': {name}' if name else ''}")

    wifi = payload.get("wifi") or {}
    if wifi.get("included"):
        name = (wifi.get("name") or "").strip()
        lines.append(f"Wi-Fi{f': {name}' if name else ''}")

    specialty_dining = payload.get("specialty_dining") or {}
    if specialty_dining.get("included"):
        name = (specialty_dining.get("name") or "").strip()
        lines.append(f"Specialty dining{f': {name}' if name else ''}")

    if payload.get("tips"):
        lines.append("Gratuities / tips included")
    if payload.get("excursion"):
        lines.append("Shore excursion included")

    excursion_credit = payload.get("excursion_credit") or {}
    if excursion_credit.get("included"):
        lines.append(f"Excursion credit: {_format_money(excursion_credit.get('amount') or 0)}")

    onboard_credit = payload.get("onboard_credit") or {}
    if onboard_credit.get("included"):
        lines.append(f"Cruise line OBC: {_format_money(onboard_credit.get('amount') or 0)}")

    gift_obc = payload.get("gift_obc") or {}
    if gift_obc.get("included"):
        lines.append(f"Gift OBC: {_format_money(gift_obc.get('amount') or 0)}")

    return lines or ["Standard inclusions per cruise line policy"]


def _paragraph_html(text: str) -> str:
    safe = escape(text.strip())
    if not safe:
        return ""
    return (
        f'<p style="margin:0 0 16px;font-size:16px;line-height:1.65;color:#243b53;">'
        f"{safe.replace(chr(10), '<br />')}"
        f"</p>"
    )


def _itinerary_lines_for_cruise(cruise: ProposedCruise) -> list[str]:
    details = (cruise.itinerary_details or "").strip()
    if details:
        return [line.strip() for line in details.splitlines() if line.strip()]
    return []


def _format_passenger_names(passengers: list[RequestPassengerRead]) -> str:
    if not passengers:
        return "Unassigned"
    names: list[str] = []
    for passenger in passengers:
        name = f"{passenger.first_name} {passenger.last_name}".strip()
        if name:
            names.append(name)
    return ", ".join(names) if names else "Unassigned"


def _format_room_title(
    cabin_index: int,
    cabins_needed: int,
    room_category: str,
    room_number: str,
) -> str:
    room_label = f"Room {cabin_index + 1}" if cabins_needed > 1 else "Cabin"
    parts = [room_label]
    if room_category.strip():
        parts.append(room_category.strip())
    if room_number.strip():
        parts.append(f"#{room_number.strip()}")
    return " · ".join(parts)


def _includes_list_html(includes: dict[str, Any] | None) -> str:
    includes_items = "".join(
        f'<li style="margin:0 0 6px;">{escape(line)}</li>' for line in _format_includes(includes)
    )
    return (
        f'<ul style="margin:8px 0 0;padding-left:20px;color:#334e68;line-height:1.55;">{includes_items}</ul>'
        if includes_items
        else ""
    )


def _render_room_block_html(
    *,
    cabin_index: int,
    cabins_needed: int,
    room: ProposedCruiseRoom,
    passengers: list[RequestPassengerRead],
) -> str:
    title = _format_room_title(cabin_index, cabins_needed, room.room_category, room.room_number)
    passenger_text = _format_passenger_names(passengers)
    includes_html = _includes_list_html(_includes_payload(room.includes))

    return f"""
      <div style="margin:0 0 16px;padding:14px 16px;border-radius:10px;background:#f8fafc;border:1px solid #d9e2ec;">
        <div style="font-size:15px;font-weight:700;color:#102a43;">{escape(title)}</div>
        <div style="margin-top:10px;font-size:13px;color:#486581;">
          <span style="font-weight:700;text-transform:uppercase;letter-spacing:0.05em;">Passengers</span>
          <div style="margin-top:4px;font-size:15px;color:#102a43;">{escape(passenger_text)}</div>
        </div>
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:14px 0 0;">
          <tr>
            <td width="50%" valign="top" style="padding:10px 10px 0 0;">
              <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#047857;">Room deposit</div>
              <div style="margin-top:4px;font-size:17px;font-weight:700;color:#065f46;">{_format_money(room.deposit_amount)}</div>
            </td>
            <td width="50%" valign="top" style="padding:10px 0 0 10px;">
              <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#1d4ed8;">Room total</div>
              <div style="margin-top:4px;font-size:17px;font-weight:700;color:#1e3a8a;">{_format_money(room.cost)}</div>
            </td>
          </tr>
        </table>
        <div style="margin-top:12px;font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Included with this room</div>
        {includes_html}
      </div>
    """


def _render_overall_pricing_html(cruise: ProposedCruise) -> str:
    return f"""
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 16px;">
        <tr>
          <td width="33%" valign="top" style="padding:12px;background:#ecfdf5;border:1px solid #abefc6;border-radius:10px 0 0 10px;">
            <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#047857;">Total cost</div>
            <div style="margin-top:4px;font-size:18px;font-weight:700;color:#065f46;">{_format_money(cruise.cost)}</div>
          </td>
          <td width="34%" valign="top" style="padding:12px;background:#eff6ff;border-top:1px solid #bfdbfe;border-bottom:1px solid #bfdbfe;">
            <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#1d4ed8;">Deposit</div>
            <div style="margin-top:4px;font-size:18px;font-weight:700;color:#1e3a8a;">{_format_money(cruise.deposit_amount)}</div>
            <div style="margin-top:4px;font-size:12px;color:#334e68;">Due {_format_display_date(cruise.deposit_due_date)}</div>
          </td>
          <td width="33%" valign="top" style="padding:12px;background:#fff7ed;border:1px solid #fed7aa;border-radius:0 10px 10px 0;">
            <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#c2410c;">Final payment</div>
            <div style="margin-top:4px;font-size:15px;font-weight:700;color:#9a3412;">Due {_format_display_date(cruise.final_payment_due_date)}</div>
          </td>
        </tr>
      </table>
    """


def _render_cruise_option_html(
    *,
    index: int,
    cruise: ProposedCruise,
    cabins_needed: int,
) -> str:
    cabin_rooms = cabin_rooms_from_cruise(cruise, cabins_needed)
    room_passengers = build_room_passengers_from_links(cruise, cabins_needed)
    multi_room = len(cabin_rooms) > 1

    highlights = _itinerary_lines_for_cruise(cruise)
    itinerary_items = "".join(
        f'<li style="margin:0 0 8px;">{escape(line)}</li>' for line in highlights
    )
    itinerary_body = (
        f'<ul style="margin:8px 0 0;padding-left:20px;color:#334e68;line-height:1.55;">{itinerary_items}</ul>'
        if itinerary_items
        else (
            f'<p style="margin:8px 0 0;font-size:15px;line-height:1.6;color:#334e68;">'
            f"{escape(cruise.itinerary_name)}"
            f"</p>"
        )
    )

    if multi_room:
        room_blocks = "".join(
            _render_room_block_html(
                cabin_index=cabin_index,
                cabins_needed=cabins_needed,
                room=room,
                passengers=room_passengers[cabin_index] if cabin_index < len(room_passengers) else [],
            )
            for cabin_index, room in enumerate(cabin_rooms)
        )
        room_section = f"""
          <div style="margin:0 0 16px;">
            <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Rooms in this option</div>
            <div style="margin-top:10px;">{room_blocks}</div>
          </div>
          <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Overall pricing</div>
          {_render_overall_pricing_html(cruise)}
        """
    else:
        room = cabin_rooms[0]
        passengers = room_passengers[0] if room_passengers else []
        passenger_text = _format_passenger_names(passengers)
        includes_html = _includes_list_html(_includes_payload(room.includes))
        room_section = f"""
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 16px;">
            <tr>
              <td width="50%" valign="top" style="padding:0 10px 12px 0;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Departure</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{_format_display_date(cruise.departure_date)}</div>
              </td>
              <td width="50%" valign="top" style="padding:0 0 12px 10px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Duration</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{cruise.number_of_nights} nights</div>
              </td>
            </tr>
            <tr>
              <td width="50%" valign="top" style="padding:0 10px 0 0;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Cabin</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{escape(room.room_category)}</div>
              </td>
              <td width="50%" valign="top" style="padding:0 0 0 10px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Passengers</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{escape(passenger_text)}</div>
              </td>
            </tr>
          </table>

          <div style="margin:0 0 16px;padding:14px 16px;border-radius:10px;background:#f0f4f8;border:1px solid #d9e2ec;">
            <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Itinerary</div>
            <div style="margin-top:6px;font-size:16px;font-weight:700;color:#102a43;">{escape(cruise.itinerary_name)}</div>
            {itinerary_body}
          </div>

          {_render_overall_pricing_html(cruise)}

          <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Included with this option</div>
          {includes_html}
        """

    shared_trip_meta = ""
    if multi_room:
        shared_trip_meta = f"""
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 16px;">
            <tr>
              <td width="50%" valign="top" style="padding:0 10px 12px 0;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Departure</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{_format_display_date(cruise.departure_date)}</div>
              </td>
              <td width="50%" valign="top" style="padding:0 0 12px 10px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#627d98;">Duration</div>
                <div style="margin-top:4px;font-size:15px;color:#102a43;">{cruise.number_of_nights} nights</div>
              </td>
            </tr>
          </table>

          <div style="margin:0 0 16px;padding:14px 16px;border-radius:10px;background:#f0f4f8;border:1px solid #d9e2ec;">
            <div style="font-size:12px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;color:#486581;">Itinerary</div>
            <div style="margin-top:6px;font-size:16px;font-weight:700;color:#102a43;">{escape(cruise.itinerary_name)}</div>
            {itinerary_body}
          </div>
        """

    return f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px;border:1px solid #d9e2ec;border-radius:12px;overflow:hidden;background:#ffffff;">
              <tr>
                <td style="padding:14px 18px;background:linear-gradient(135deg,#102a43 0%,#243b53 100%);color:#ffffff;">
                  <div style="font-size:12px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.85;">Option {index}</div>
                  <div style="margin-top:4px;font-size:20px;font-weight:700;line-height:1.3;">{escape(cruise.cruise_line)} · {escape(cruise.ship)}</div>
                </td>
              </tr>
              <tr>
                <td style="padding:18px;">
                  {shared_trip_meta}
                  {room_section}
                </td>
              </tr>
            </table>
            """


def _render_proposal_header_html(branding: AgencyEmailBranding | None) -> str:
    if branding is not None:
        logo_html = render_email_brand_logo_img(branding, width=180, centered=True)
        return f"""
                <div style="text-align:center;">{logo_html}</div>
                <h1 style="margin:16px 0 0;font-size:28px;line-height:1.25;font-weight:700;text-align:center;">Your cruise options</h1>
                <p style="margin:10px 0 0;font-size:15px;line-height:1.6;opacity:0.92;text-align:center;">A personalized proposal from {escape(branding.agency_name)}</p>
        """

    return f"""
                <div style="font-size:12px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.82;">{escape(BRAND_NAME)}</div>
                <h1 style="margin:10px 0 0;font-size:28px;line-height:1.25;font-weight:700;">Your cruise options</h1>
                <p style="margin:10px 0 0;font-size:15px;line-height:1.6;opacity:0.92;">A personalized proposal prepared for you</p>
    """


def build_research_proposal_email_html(
    *,
    intro: str,
    closing: str,
    cruises: list[ProposedCruise],
    branding: AgencyEmailBranding | None = None,
    cabins_needed: int = 1,
) -> str:
    safe_cabins_needed = max(1, cabins_needed)
    option_blocks = [
        _render_cruise_option_html(index=index, cruise=cruise, cabins_needed=safe_cabins_needed)
        for index, cruise in enumerate(cruises, start=1)
    ]

    intro_html = _paragraph_html(intro)
    closing_html = _paragraph_html(closing)
    options_html = "".join(option_blocks)
    header_html = _render_proposal_header_html(branding)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cruise proposal</title>
  </head>
  <body style="margin:0;padding:0;background:#eef2f7;font-family:Georgia, 'Times New Roman', serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef2f7;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(16,42,67,0.12);">
            <tr>
              <td style="padding:28px 28px 18px;background:linear-gradient(180deg,#eef2f7 0%,#dce4ed 100%);color:#1e293b;border-bottom:1px solid #c8d3e0;">
                {header_html}
              </td>
            </tr>
            <tr>
              <td style="padding:28px;">
                {RESEARCH_PROPOSAL_CONTENT_START}
                {intro_html}
                {options_html}
                {closing_html}
                {RESEARCH_PROPOSAL_CONTENT_END}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""
