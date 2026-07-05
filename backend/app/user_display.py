from __future__ import annotations

import re


def format_username_display_name(username: str) -> str:
    """Turn a login username (e.g. robert.binetti) into a display name (Robert Binetti)."""
    raw = (username or "").strip()
    if not raw:
        return ""

    parts = [part for part in re.split(r"[._\-]+", raw) if part]
    if not parts:
        return raw[:1].upper() + raw[1:].lower()

    formatted: list[str] = []
    for part in parts:
        lowered = part.lower()
        formatted.append(lowered[:1].upper() + lowered[1:] if lowered else "")

    return " ".join(formatted)
