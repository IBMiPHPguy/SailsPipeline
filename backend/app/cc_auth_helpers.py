from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models import ProposedCruise, TravelRequest
from app.proposed_cruise_helpers import normalize_cabin_pricing_list


@dataclass(frozen=True)
class CcAuthCruiseSummary:
    cruise_line: str
    ship: str
    sailing_date: date
    cabin_type: str
    deposit_amount: Decimal
    final_payment_due_date: date


def _reservation_count_for_cabin(reservation_ids: list[list[str]], cabin_index: int) -> int:
    if cabin_index >= len(reservation_ids):
        return 1
    active = [value.strip() for value in reservation_ids[cabin_index] if value and value.strip()]
    return max(1, len(active))


def compute_cruise_deposit_due(cruise: ProposedCruise, cabins_needed: int) -> Decimal:
    safe_cabins_needed = max(1, cabins_needed)
    pricing = normalize_cabin_pricing_list(
        cruise.cabin_pricing,
        safe_cabins_needed,
        deposit_amount=Decimal(str(cruise.deposit_amount)),
        cost=Decimal(str(cruise.cost)),
    )
    reservation_ids = cruise.cabin_hold_reservation_ids or []
    total = Decimal("0")
    for cabin_index, cabin in enumerate(pricing):
        deposit = Decimal(str(cabin["deposit_amount"]))
        room_count = _reservation_count_for_cabin(reservation_ids, cabin_index)
        total += deposit * room_count
    return total


def build_cc_auth_cruise_summaries(
    request: TravelRequest,
    accepted_cruises: list[ProposedCruise],
) -> tuple[list[CcAuthCruiseSummary], Decimal]:
    cabins_needed = max(1, request.cabins_needed)
    summaries: list[CcAuthCruiseSummary] = []
    total_deposit = Decimal("0")

    for cruise in sorted(accepted_cruises, key=lambda item: (item.departure_date, item.id)):
        deposit_amount = compute_cruise_deposit_due(cruise, cabins_needed)
        total_deposit += deposit_amount
        summaries.append(
            CcAuthCruiseSummary(
                cruise_line=cruise.cruise_line,
                ship=cruise.ship,
                sailing_date=cruise.departure_date,
                cabin_type=cruise.room_category,
                deposit_amount=deposit_amount,
                final_payment_due_date=cruise.final_payment_due_date,
            )
        )

    return summaries, total_deposit
