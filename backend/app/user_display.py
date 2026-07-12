from __future__ import annotations

import re


def split_username_parts(username: str) -> list[str]:
    """Split a login username into name parts (e.g. robert.binetti -> ['robert', 'binetti'])."""
    raw = (username or "").strip()
    if not raw:
        return []
    return [part for part in re.split(r"[._\-]+", raw) if part]


def _title_case_part(part: str) -> str:
    lowered = part.lower()
    return lowered[:1].upper() + lowered[1:] if lowered else ""


def format_username_display_name(username: str) -> str:
    """Turn a login username (e.g. robert.binetti) into a display name (Robert Binetti)."""
    parts = split_username_parts(username)
    if not parts:
        raw = (username or "").strip()
        return raw[:1].upper() + raw[1:].lower() if raw else ""
    return " ".join(_title_case_part(part) for part in parts)


def username_first_last(username: str) -> tuple[str, str]:
    """Derive first and last name from a username; last may be empty for single-part names."""
    parts = split_username_parts(username)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return _title_case_part(parts[0]), ""
    return _title_case_part(parts[0]), _title_case_part(parts[-1])


def username_initials(username: str) -> str:
    """Two-letter initials from username (e.g. robert.binetti -> RB)."""
    first, last = username_first_last(username)
    if first and last:
        return f"{first[0]}{last[0]}".upper()
    if first:
        return first[:2].upper()
    return "?"
