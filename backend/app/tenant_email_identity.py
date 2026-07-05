from __future__ import annotations

import re

from email.utils import formataddr

_CONCIERGE_SUFFIX = "Concierge"


def build_agency_email_local_part(agency_name: str) -> str:
    """Build a safe alphanumeric local-part prefix from the tenant display name."""
    words = agency_name.strip().split()
    parts: list[str] = []
    for word in words:
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", word)
        if not cleaned:
            continue
        if len(cleaned) == 1:
            parts.append(cleaned.upper())
        else:
            parts.append(cleaned[0].upper() + cleaned[1:].lower())

    prefix = "".join(parts) or "Agency"
    return f"{prefix}{_CONCIERGE_SUFFIX}"


def build_tenant_from_header(*, agency_name: str, mail_domain: str) -> str:
    """Format: \"Agency Name\" <SafePrefixConcierge@mail.sailspipeline.com>"""
    display_name = agency_name.strip() or "Your travel agency"
    local_part = build_agency_email_local_part(display_name)
    mailbox = f"{local_part}@{mail_domain.strip()}"
    return formataddr((display_name, mailbox))
