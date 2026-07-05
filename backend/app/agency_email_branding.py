from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

from sqlalchemy.orm import Session

from app.branding import BRAND_NAME
from app.config import settings
from app.services.agency_settings_service import (
    DEFAULT_PRIMARY_COLOR,
    DEFAULT_SECONDARY_COLOR,
    get_agency_settings_row,
)

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
_STATIC_UPLOADS_PREFIX = "/static/uploads/"
_STATIC_ASSET_PREFIX = "/static/"
_EMAIL_IMG_SRC_PATTERN = re.compile(
    r'(<img\b[^>]*\bsrc=["\'])([^"\']+)(["\'])',
    re.IGNORECASE,
)


def contrast_text_color(hex_color: str) -> str:
    normalized = hex_color.strip().lstrip("#")
    if len(normalized) != 6:
        return "#ffffff"
    try:
        red = int(normalized[0:2], 16)
        green = int(normalized[2:4], 16)
        blue = int(normalized[4:6], 16)
    except ValueError:
        return "#ffffff"
    yiq = (red * 299 + green * 587 + blue * 114) / 1000
    return "#111111" if yiq >= 128 else "#ffffff"


def normalize_brand_hex(color: str | None, *, default: str) -> str:
    if color and _HEX_COLOR_PATTERN.match(color.strip()):
        return color.strip()
    return default


def resolve_brand_asset_public_base_url() -> str:
    return settings.resolved_brand_asset_public_base_url


def _normalize_asset_path(url: str) -> str:
    stripped = url.strip()
    if stripped.startswith(("http://", "https://")):
        for marker in (_STATIC_UPLOADS_PREFIX, _STATIC_ASSET_PREFIX):
            marker_index = stripped.find(marker)
            if marker_index != -1:
                return stripped[marker_index:]
        return stripped

    if stripped.startswith("static/"):
        return f"/{stripped}"
    if not stripped.startswith("/"):
        return f"/{stripped}"
    return stripped


def resolve_absolute_brand_asset_url(url: str | None, *, public_base_url: str | None = None) -> str | None:
    """Convert stored brand asset paths to fully qualified URLs for email clients."""
    if not url or not url.strip():
        return None

    base = (public_base_url or resolve_brand_asset_public_base_url()).rstrip("/")
    normalized = _normalize_asset_path(url.strip())

    if normalized.startswith(("http://", "https://")):
        return normalized

    return f"{base}{normalized}"


def absolutize_email_html_asset_urls(html: str | None) -> str:
    """Rewrite relative /static asset paths inside email HTML fragments to absolute URLs."""
    if not html:
        return ""

    base = resolve_brand_asset_public_base_url()

    def _replace_img_src(match: re.Match[str]) -> str:
        prefix, src, suffix = match.groups()
        absolute = resolve_absolute_brand_asset_url(src, public_base_url=base)
        if not absolute:
            return match.group(0)
        return f'{prefix}{escape(absolute, quote=True)}{suffix}'

    return _EMAIL_IMG_SRC_PATTERN.sub(_replace_img_src, html)


@dataclass(frozen=True)
class AgencyEmailBranding:
    agency_id: str
    agency_name: str
    brand_logo_url: str | None
    brand_logo_absolute_url: str | None
    primary_color: str
    secondary_color: str
    primary_text_color: str
    email_signature_block: str | None


def load_agency_email_branding(db: Session, *, agency_id: str) -> AgencyEmailBranding:
    row = get_agency_settings_row(db, agency_id=agency_id)
    primary = normalize_brand_hex(row.primary_color, default=DEFAULT_PRIMARY_COLOR)
    secondary = normalize_brand_hex(row.secondary_color, default=DEFAULT_SECONDARY_COLOR)
    asset_base = resolve_brand_asset_public_base_url()
    logo_absolute = resolve_absolute_brand_asset_url(row.brand_logo_url, public_base_url=asset_base)
    agency_name = (row.agency_name or "").strip() or "Your travel agency"
    signature_raw = (row.email_signature_block or "").strip()
    signature = absolutize_email_html_asset_urls(signature_raw) or None
    return AgencyEmailBranding(
        agency_id=row.agency_id,
        agency_name=agency_name,
        brand_logo_url=row.brand_logo_url,
        brand_logo_absolute_url=logo_absolute,
        primary_color=primary,
        secondary_color=secondary,
        primary_text_color=contrast_text_color(primary),
        email_signature_block=signature,
    )


def render_email_brand_logo_img(
    branding: AgencyEmailBranding,
    *,
    width: int = 200,
    alt: str | None = None,
    centered: bool = False,
) -> str:
    safe_alt = escape(alt or branding.agency_name)
    if branding.brand_logo_absolute_url:
        safe_logo = escape(branding.brand_logo_absolute_url, quote=True)
        center_style = "margin:0 auto;" if centered else ""
        return (
            f'<img src="{safe_logo}" alt="{safe_alt}" width="{width}" '
            f'style="display:block;{center_style}max-width:{width}px;width:100%;height:auto;border:0;" />'
        )

    safe_agency = escape(branding.agency_name)
    safe_primary = escape(branding.primary_color)
    text_align = "text-align:center;" if centered else ""
    return (
        f'<div style="font-size:24px;font-weight:700;line-height:1.25;color:{safe_primary};{text_align}">'
        f"{safe_agency}</div>"
    )


def render_email_brand_header_html(branding: AgencyEmailBranding, *, agent_name: str) -> str:
    safe_agent = escape(agent_name)
    safe_agency = escape(branding.agency_name)
    safe_primary = escape(branding.primary_color)
    safe_secondary = escape(branding.secondary_color)
    brand_markup = render_email_brand_logo_img(branding, width=200, alt=branding.agency_name)

    return f"""
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td class="email-header-cell"
      style="padding:28px 32px 20px;background:linear-gradient(180deg,#f8fbff 0%,#eef4fa 100%);
        border-bottom:2px solid {safe_primary};">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td style="padding:0 0 14px;">{brand_markup}</td>
        </tr>
        <tr>
          <td style="padding:0;">
            <div style="font-size:11px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
              color:{safe_secondary};margin-bottom:6px;">Your travel advisor</div>
            <div style="font-size:20px;font-weight:700;line-height:1.3;color:#102a43;">{safe_agent}</div>
            <div style="margin-top:4px;font-size:14px;line-height:1.5;color:#486581;">{safe_agency}</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
""".strip()


def render_email_cta_button(
    *,
    href: str,
    label: str,
    primary_color: str,
    text_color: str | None = None,
) -> str:
    safe_href = escape(href, quote=True)
    safe_label = escape(label)
    safe_primary = escape(primary_color)
    safe_text = escape(text_color or contrast_text_color(primary_color))
    return (
        f'<a href="{safe_href}" '
        f'style="display:inline-block;padding:14px 28px;background:{safe_primary};color:{safe_text};'
        f"text-decoration:none;border-radius:8px;font-size:16px;font-weight:700;\">"
        f"{safe_label}</a>"
    )


def render_email_signature_section(signature_html: str | None) -> str:
    if not signature_html:
        return ""
    return (
        '<div style="margin-top:28px;padding-top:20px;border-top:1px solid #d9e2ec;'
        'font-size:15px;line-height:1.6;color:#334e68;word-break:break-word;overflow-wrap:anywhere;">'
        f"{absolutize_email_html_asset_urls(signature_html)}"
        "</div>"
    )


def render_platform_compliance_footer(*, agent_name: str, agency_name: str) -> str:
    safe_agent = escape(agent_name)
    safe_agency = escape(agency_name)
    safe_platform = escape(BRAND_NAME)
    return f"""
<p style="margin:0;font-size:12px;line-height:1.6;color:#627d98;text-align:center;">
  This email was securely delivered on behalf of
  <strong style="color:#334e68;">{safe_agent}</strong> at
  <strong style="color:#334e68;">{safe_agency}</strong> via {safe_platform} CRM.
</p>
<p style="margin:12px 0 0;font-size:11px;line-height:1.5;color:#829ab1;text-align:center;">
  Please reply directly to this message to reach your travel advisor.
</p>
""".strip()
