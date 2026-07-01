"""Agency group shell validation and read helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants import CABIN_TYPES
from app.models import AgencyGroup, AgencyGroupInventory
from app.schemas import normalize_cruise_line_value
from app.services.agency_service import NOT_FOUND, require_record_for_agency

DEFAULT_TC_RATIO = "1:16"


class AgencyGroupValidationError(ValueError):
    pass


def compute_cabins_remaining(*, cabins_allocated: int, cabins_reserved: int) -> int:
    return max(0, cabins_allocated - cabins_reserved)


def validate_group_dates(*, sailing_date: date, disembarkation_date: date) -> None:
    if disembarkation_date < sailing_date:
        raise AgencyGroupValidationError("Disembarkation date must be on or after sailing date.")


def validate_inventory_counts(
    *,
    cabins_allocated: int,
    cabins_reserved: int = 0,
    price_per_cabin: Decimal | float | int = 0,
) -> None:
    if cabins_allocated < 0:
        raise AgencyGroupValidationError("Cabins allocated cannot be negative.")
    if cabins_reserved < 0:
        raise AgencyGroupValidationError("Cabins reserved cannot be negative.")
    if cabins_reserved > cabins_allocated:
        raise AgencyGroupValidationError("Cabins reserved cannot exceed cabins allocated.")
    if Decimal(str(price_per_cabin)) < 0:
        raise AgencyGroupValidationError("Price per cabin cannot be negative.")


def validate_cabin_type(value: str) -> str:
    normalized = value.strip()
    if normalized not in CABIN_TYPES:
        raise AgencyGroupValidationError("Invalid cabin type selected.")
    return normalized


def normalize_tc_ratio(value: str | None) -> str:
    if value is None or not str(value).strip():
        return DEFAULT_TC_RATIO
    return str(value).strip()


def validate_group_fields(
    *,
    cruise_line: str,
    sailing_date: date,
    disembarkation_date: date,
    tc_ratio: str | None = None,
) -> str:
    validate_group_dates(sailing_date=sailing_date, disembarkation_date=disembarkation_date)
    return normalize_cruise_line_value(cruise_line)


def validate_group_create(
    *,
    cruise_line: str,
    sailing_date: date,
    disembarkation_date: date,
    tc_ratio: str | None = None,
    inventory_rows: list[dict] | None = None,
) -> str:
    normalized_line = validate_group_fields(
        cruise_line=cruise_line,
        sailing_date=sailing_date,
        disembarkation_date=disembarkation_date,
        tc_ratio=tc_ratio,
    )
    for row in inventory_rows or []:
        validate_inventory_row_payload(row)
    return normalized_line


def validate_inventory_row_payload(row: dict) -> None:
    cabin_type = validate_cabin_type(str(row.get("cabin_type", "")))
    row["cabin_type"] = cabin_type
    validate_inventory_counts(
        cabins_allocated=int(row.get("cabins_allocated", 0)),
        cabins_reserved=int(row.get("cabins_reserved", 0)),
        price_per_cabin=row.get("price_per_cabin", 0),
    )


def validate_group_update(
    group: AgencyGroup,
    *,
    cruise_line: str | None = None,
    sailing_date: date | None = None,
    disembarkation_date: date | None = None,
    tc_ratio: str | None = None,
) -> None:
    next_sailing = sailing_date if sailing_date is not None else group.sailing_date
    next_disembarkation = (
        disembarkation_date if disembarkation_date is not None else group.disembarkation_date
    )
    next_line = cruise_line if cruise_line is not None else group.cruise_line
    validate_group_fields(
        cruise_line=next_line,
        sailing_date=next_sailing,
        disembarkation_date=next_disembarkation,
        tc_ratio=tc_ratio,
    )


def validate_inventory_update(
    inventory: AgencyGroupInventory,
    *,
    cabins_allocated: int | None = None,
    cabins_reserved: int | None = None,
    price_per_cabin: Decimal | float | int | None = None,
    cabin_type: str | None = None,
) -> None:
    if cabin_type is not None:
        validate_cabin_type(cabin_type)
    validate_inventory_counts(
        cabins_allocated=cabins_allocated if cabins_allocated is not None else inventory.cabins_allocated,
        cabins_reserved=cabins_reserved if cabins_reserved is not None else inventory.cabins_reserved,
        price_per_cabin=price_per_cabin if price_per_cabin is not None else inventory.price_per_cabin,
    )


def get_agency_group_for_agency(db: Session, group_id: str, agency_id: str) -> AgencyGroup:
    group = db.get(AgencyGroup, group_id)
    return require_record_for_agency(group, agency_id=agency_id)


def get_agency_group_inventory_for_agency(
    db: Session,
    inventory_id: str,
    agency_id: str,
) -> AgencyGroupInventory:
    inventory = db.get(AgencyGroupInventory, inventory_id)
    if inventory is None:
        raise NOT_FOUND
    require_record_for_agency(inventory.group, agency_id=agency_id)
    return inventory


def validate_travel_request_group_linkage(
    db: Session,
    *,
    agency_id: str,
    group_id: str | None,
    group_inventory_id: str | None,
) -> None:
    if group_id is None and group_inventory_id is None:
        return
    if group_inventory_id is not None and group_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_id is required when group_inventory_id is set.",
        )

    group = get_agency_group_for_agency(db, group_id, agency_id)
    if not group.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected agency group is not active.",
        )

    if group_inventory_id is None:
        return

    inventory = get_agency_group_inventory_for_agency(db, group_inventory_id, agency_id)
    if inventory.group_id != group.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group inventory does not belong to the selected group.",
        )


def inventory_row_read_payload(inventory: AgencyGroupInventory) -> dict:
    remaining = compute_cabins_remaining(
        cabins_allocated=inventory.cabins_allocated,
        cabins_reserved=inventory.cabins_reserved,
    )
    return {
        "id": inventory.id,
        "group_id": inventory.group_id,
        "cabin_category": inventory.cabin_category,
        "cabin_type": inventory.cabin_type,
        "cabin_description": inventory.cabin_description,
        "price_per_cabin": float(inventory.price_per_cabin),
        "cabins_allocated": inventory.cabins_allocated,
        "cabins_reserved": inventory.cabins_reserved,
        "cabins_remaining": remaining,
        "created_at": inventory.created_at,
        "updated_at": inventory.updated_at,
    }


def group_summary_rollups(group: AgencyGroup) -> dict:
    total_allocated = 0
    total_reserved = 0
    for item in group.inventory_items:
        total_allocated += item.cabins_allocated
        total_reserved += item.cabins_reserved
    return {
        "inventory_row_count": len(group.inventory_items),
        "total_cabins_allocated": total_allocated,
        "total_cabins_reserved": total_reserved,
        "total_cabins_remaining": max(0, total_allocated - total_reserved),
    }
