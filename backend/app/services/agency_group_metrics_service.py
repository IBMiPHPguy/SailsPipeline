"""Aggregated operational metrics for agency group blocks."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.constants import PRIMARY_CLOSE_REASON, REQUEST_STATUS_CLOSED, REQUEST_STATUS_OPEN
from app.group_tc import BERTHS_PER_GROUP_CABIN, compute_tc_progress, format_tc_progress_message
from app.models import TravelRequest
from app.services.agency_group_service import compute_cabins_remaining, get_agency_group_detail


def liquidation_tone(*, allocated: int, reserved: int, remaining: int) -> str:
    if allocated <= 0:
        return "healthy"
    if remaining <= 0:
        return "sold_out"
    if reserved / allocated >= 0.8:
        return "nearing_sellout"
    return "healthy"


def liquidation_percent(*, allocated: int, reserved: int) -> float:
    if allocated <= 0:
        return 0.0
    return round(min(100.0, max(0.0, (reserved / allocated) * 100.0)), 1)


def count_linked_group_requests(db: Session, *, group_id: str) -> int:
    return (
        db.query(func.count(TravelRequest.id))
        .filter(
            TravelRequest.group_id == group_id,
            (
                (TravelRequest.status == REQUEST_STATUS_OPEN)
                | (
                    (TravelRequest.status == REQUEST_STATUS_CLOSED)
                    & (TravelRequest.close_reason == PRIMARY_CLOSE_REASON)
                )
            ),
        )
        .scalar()
        or 0
    )


def build_agency_group_metrics(db: Session, *, agency_id: str, group_id: str) -> dict:
    group = get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)

    inventory_rows: list[dict] = []
    total_allocated = 0
    total_reserved = 0
    max_gross_yield = 0.0
    accrued_gross_yield = 0.0

    for item in group.inventory_items:
        allocated = int(item.cabins_allocated)
        reserved = int(item.cabins_reserved)
        remaining = compute_cabins_remaining(cabins_allocated=allocated, cabins_reserved=reserved)
        price = float(item.price_per_cabin)
        row_max_yield = price * allocated
        row_accrued_yield = price * reserved

        total_allocated += allocated
        total_reserved += reserved
        max_gross_yield += row_max_yield
        accrued_gross_yield += row_accrued_yield

        inventory_rows.append(
            {
                "inventory_id": item.id,
                "cabin_category": item.cabin_category,
                "cabins_allocated": allocated,
                "cabins_reserved": reserved,
                "cabins_remaining": remaining,
                "max_gross_yield": round(row_max_yield, 2),
                "accrued_gross_yield": round(row_accrued_yield, 2),
                "liquidation_percent": liquidation_percent(allocated=allocated, reserved=reserved),
                "liquidation_tone": liquidation_tone(
                    allocated=allocated,
                    reserved=reserved,
                    remaining=remaining,
                ),
            }
        )

    total_remaining = compute_cabins_remaining(
        cabins_allocated=total_allocated,
        cabins_reserved=total_reserved,
    )
    tc_progress = compute_tc_progress(
        total_cabins_reserved=total_reserved,
        tc_ratio=group.tc_ratio,
    )

    return {
        "group_id": group.id,
        "linked_request_count": count_linked_group_requests(db, group_id=group.id),
        "totals": {
            "cabins_allocated": total_allocated,
            "cabins_reserved": total_reserved,
            "cabins_remaining": total_remaining,
            "max_gross_yield": round(max_gross_yield, 2),
            "accrued_gross_yield": round(accrued_gross_yield, 2),
            "remaining_gross_yield": round(max(0.0, max_gross_yield - accrued_gross_yield), 2),
            "liquidation_percent": liquidation_percent(allocated=total_allocated, reserved=total_reserved),
            "liquidation_tone": liquidation_tone(
                allocated=total_allocated,
                reserved=total_reserved,
                remaining=total_remaining,
            ),
        },
        "inventory_rows": inventory_rows,
        "tour_conductor": {
            "ratio_label": tc_progress.ratio_label,
            "berths_per_credit": tc_progress.berths_per_credit,
            "tc_per_credit": tc_progress.berths_per_credit,
            "used_default_ratio": tc_progress.used_default_ratio,
            "total_cabins_reserved": tc_progress.total_cabins_reserved,
            "total_berths_reserved": tc_progress.total_berths_reserved,
            "tc_credits_earned": tc_progress.tc_credits_earned,
            "berths_until_next_tc": tc_progress.berths_until_next_tc,
            "cabins_until_next_tc": tc_progress.berths_until_next_tc // BERTHS_PER_GROUP_CABIN
            if tc_progress.berths_until_next_tc % BERTHS_PER_GROUP_CABIN == 0
            else (tc_progress.berths_until_next_tc + 1) // BERTHS_PER_GROUP_CABIN,
            "message": format_tc_progress_message(tc_progress),
        },
    }
