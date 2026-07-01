"""Tour Conductor ratio parsing and progress calculations."""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_TC_RATIO = "1:16"
DEFAULT_BERTHS_PER_CREDIT = 16
BERTHS_PER_GROUP_CABIN = 2

_TC_RATIO_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")


@dataclass(frozen=True)
class TcRatioParseResult:
    berths_per_credit: int
    ratio_label: str
    used_default: bool


@dataclass(frozen=True)
class TcProgress:
    berths_per_credit: int
    ratio_label: str
    used_default_ratio: bool
    total_cabins_reserved: int
    total_berths_reserved: int
    tc_credits_earned: int
    berths_until_next_tc: int


def berths_from_group_cabins(cabins_reserved: int) -> int:
    """Each sold group cabin counts as two berths (no solo supplement)."""
    return max(0, int(cabins_reserved)) * BERTHS_PER_GROUP_CABIN


def parse_tc_ratio(value: str | None) -> TcRatioParseResult:
    normalized = (value or "").strip()
    if not normalized:
        return TcRatioParseResult(
            berths_per_credit=DEFAULT_BERTHS_PER_CREDIT,
            ratio_label=DEFAULT_TC_RATIO,
            used_default=True,
        )

    match = _TC_RATIO_PATTERN.match(normalized)
    if match is None:
        return TcRatioParseResult(
            berths_per_credit=DEFAULT_BERTHS_PER_CREDIT,
            ratio_label=DEFAULT_TC_RATIO,
            used_default=True,
        )

    left = int(match.group(1))
    right = int(match.group(2))
    if left < 1 or right < 1:
        return TcRatioParseResult(
            berths_per_credit=DEFAULT_BERTHS_PER_CREDIT,
            ratio_label=DEFAULT_TC_RATIO,
            used_default=True,
        )

    berths_per_credit = right // left if left > 0 else right
    if berths_per_credit < 1:
        return TcRatioParseResult(
            berths_per_credit=DEFAULT_BERTHS_PER_CREDIT,
            ratio_label=DEFAULT_TC_RATIO,
            used_default=True,
        )

    return TcRatioParseResult(
        berths_per_credit=berths_per_credit,
        ratio_label=f"{left}:{right}",
        used_default=False,
    )


def compute_tc_progress(
    *,
    total_cabins_reserved: int,
    tc_ratio: str | None,
) -> TcProgress:
    safe_cabins = max(0, int(total_cabins_reserved))
    total_berths = berths_from_group_cabins(safe_cabins)
    parsed = parse_tc_ratio(tc_ratio)
    berths_per_credit = parsed.berths_per_credit
    remainder = total_berths % berths_per_credit
    berths_until_next = berths_per_credit - remainder if remainder else berths_per_credit

    return TcProgress(
        berths_per_credit=berths_per_credit,
        ratio_label=parsed.ratio_label,
        used_default_ratio=parsed.used_default,
        total_cabins_reserved=safe_cabins,
        total_berths_reserved=total_berths,
        tc_credits_earned=total_berths // berths_per_credit,
        berths_until_next_tc=berths_until_next,
    )


def format_tc_progress_message(progress: TcProgress) -> str:
    berths = progress.total_berths_reserved
    cabins = progress.total_cabins_reserved

    if berths <= 0:
        return (
            f"No berths counted yet. {progress.berths_until_next_tc} more berths until your first "
            "Tour Conductor credit is earned!"
        )

    cabin_clause = f"{cabins} cabin{'s' if cabins != 1 else ''} sold"
    if progress.tc_credits_earned > 0 and berths % progress.berths_per_credit == 0:
        credits_label = "credit" if progress.tc_credits_earned == 1 else "credits"
        return (
            f"{berths} berths counted ({cabin_clause}). {progress.tc_credits_earned} Tour Conductor "
            f"{credits_label} earned. {progress.berths_until_next_tc} more berths until your next "
            "Tour Conductor credit is earned!"
        )

    return (
        f"{berths} berths counted ({cabin_clause}). {progress.berths_until_next_tc} more berths until "
        "your next Tour Conductor credit is earned!"
    )
