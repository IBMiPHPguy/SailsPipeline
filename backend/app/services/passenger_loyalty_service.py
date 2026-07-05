from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas import validate_cruise_line_values
from app.models import Passenger, PassengerLoyaltyNumber


def sync_passenger_loyalty_numbers(
    db: Session,
    *,
    passenger: Passenger,
    entries: list[dict[str, str]] | None,
) -> None:
    if entries is None:
        return

    normalized: list[tuple[str, str]] = []
    seen_lines: set[str] = set()
    for entry in entries:
        cruise_line = str(entry.get("cruise_line") or "").strip()
        loyalty_number = str(entry.get("loyalty_number") or "").strip()
        if not cruise_line and not loyalty_number:
            continue
        if not cruise_line or not loyalty_number:
            raise ValueError("Each loyalty number requires a cruise line and loyalty number.")
        validate_cruise_line_values([cruise_line], require_at_least_one=True)
        if cruise_line in seen_lines:
            raise ValueError("Each cruise line can only have one loyalty number.")
        seen_lines.add(cruise_line)
        normalized.append((cruise_line, loyalty_number))

    existing_by_line = {row.cruise_line: row for row in passenger.cruise_loyalty_numbers}
    keep_lines = {line for line, _ in normalized}

    for line, row in list(existing_by_line.items()):
        if line not in keep_lines:
            db.delete(row)

    for cruise_line, loyalty_number in normalized:
        existing = existing_by_line.get(cruise_line)
        if existing is None:
            db.add(
                PassengerLoyaltyNumber(
                    passenger_id=passenger.id,
                    cruise_line=cruise_line,
                    loyalty_number=loyalty_number,
                )
            )
        else:
            existing.loyalty_number = loyalty_number
