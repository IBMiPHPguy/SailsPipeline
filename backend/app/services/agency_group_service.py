"""Agency group shell validation, CRUD, and read helpers."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import String, and_, cast, false, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.constants import CABIN_TYPES
from app.models import AgencyGroup, AgencyGroupInventory, TravelRequest, TravelRequestGroupBooking
from app.schemas import normalize_cruise_line_value
from app.services.agency_service import NOT_FOUND, require_record_for_agency

DEFAULT_TC_RATIO = "1:16"
AGENCY_GROUPS_PAGE_SIZE_DEFAULT = 7
AGENCY_GROUPS_PAGE_SIZE_MAX = 50
AGENCY_GROUPS_PICKER_LIMIT = 100


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
    deposit_per_cabin: Decimal | float | int = 0,
) -> None:
    if cabins_allocated < 0:
        raise AgencyGroupValidationError("Cabins allocated cannot be negative.")
    if cabins_reserved < 0:
        raise AgencyGroupValidationError("Cabins reserved cannot be negative.")
    if cabins_reserved > cabins_allocated:
        raise AgencyGroupValidationError("Cabins reserved cannot exceed cabins allocated.")
    if Decimal(str(price_per_cabin)) < 0:
        raise AgencyGroupValidationError("Price per cabin cannot be negative.")
    if Decimal(str(deposit_per_cabin)) < 0:
        raise AgencyGroupValidationError("Deposit per cabin cannot be negative.")


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
        deposit_per_cabin=row.get("deposit_per_cabin", 0),
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
    deposit_per_cabin: Decimal | float | int | None = None,
    cabin_type: str | None = None,
) -> None:
    if cabin_type is not None and cabin_type.strip() != inventory.cabin_type:
        validate_cabin_type(cabin_type)
    validate_inventory_counts(
        cabins_allocated=cabins_allocated if cabins_allocated is not None else inventory.cabins_allocated,
        cabins_reserved=cabins_reserved if cabins_reserved is not None else inventory.cabins_reserved,
        price_per_cabin=price_per_cabin if price_per_cabin is not None else inventory.price_per_cabin,
        deposit_per_cabin=deposit_per_cabin if deposit_per_cabin is not None else inventory.deposit_per_cabin,
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
        "deposit_per_cabin": float(inventory.deposit_per_cabin),
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


def _new_id() -> str:
    return str(uuid.uuid4())


def _raise_validation_error(exc: AgencyGroupValidationError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _groups_query(db: Session, agency_id: str):
    return (
        db.query(AgencyGroup)
        .filter(AgencyGroup.agency_id == agency_id)
        .options(joinedload(AgencyGroup.inventory_items))
    )


def group_to_list_item_payload(group: AgencyGroup) -> dict:
    return {
        "id": group.id,
        "agency_id": group.agency_id,
        "created_by_id": group.created_by_id,
        "group_name": group.group_name,
        "cruise_line": group.cruise_line,
        "ship_name": group.ship_name,
        "sailing_date": group.sailing_date,
        "disembarkation_date": group.disembarkation_date,
        "group_id_code": group.group_id_code,
        "is_active": group.is_active,
        "summary": group_summary_rollups(group),
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


def group_to_read_payload(group: AgencyGroup) -> dict:
    return {
        "id": group.id,
        "agency_id": group.agency_id,
        "created_by_id": group.created_by_id,
        "group_name": group.group_name,
        "cruise_line": group.cruise_line,
        "ship_name": group.ship_name,
        "sailing_date": group.sailing_date,
        "disembarkation_date": group.disembarkation_date,
        "group_id_code": group.group_id_code,
        "group_amenities": group.group_amenities,
        "tc_ratio": normalize_tc_ratio(group.tc_ratio),
        "is_active": group.is_active,
        "inventory_items": [inventory_row_read_payload(item) for item in group.inventory_items],
        "summary": group_summary_rollups(group),
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


def list_agency_groups(
    db: Session,
    *,
    agency_id: str,
    is_active: bool | None = None,
) -> list[AgencyGroup]:
    groups, _total = list_agency_groups_page(
        db,
        agency_id=agency_id,
        is_active=is_active,
        query="",
        page=1,
        page_size=AGENCY_GROUPS_PAGE_SIZE_MAX,
    )
    return groups


def _agency_group_token_filters(token: str):
    pattern = f"%{token}%"
    return or_(
        AgencyGroup.group_name.ilike(pattern),
        AgencyGroup.cruise_line.ilike(pattern),
        AgencyGroup.ship_name.ilike(pattern),
        AgencyGroup.group_id_code.ilike(pattern),
        cast(AgencyGroup.sailing_date, String).ilike(pattern),
        cast(AgencyGroup.disembarkation_date, String).ilike(pattern),
        func.concat(AgencyGroup.cruise_line, " ", AgencyGroup.ship_name).ilike(pattern),
        func.concat(AgencyGroup.group_name, " ", AgencyGroup.cruise_line).ilike(pattern),
    )


def _agency_group_search_clause(term: str):
    tokens = [part.strip() for part in term.split() if part.strip()]
    if not tokens:
        return None
    return and_(*[_agency_group_token_filters(token) for token in tokens])


def agency_groups_total_pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return ceil(total / page_size)


def _apply_visibility_clause(query, visibility_clause):
    if visibility_clause is True:
        return query
    if visibility_clause is False:
        return query.filter(false())
    return query.filter(visibility_clause)


def _agency_groups_filtered_query(
    db: Session,
    *,
    agency_id: str,
    is_active: bool | None = None,
    query: str = "",
    visibility_clause=True,
):
    base = db.query(AgencyGroup).filter(AgencyGroup.agency_id == agency_id)
    if is_active is not None:
        base = base.filter(AgencyGroup.is_active == is_active)
    search_clause = _agency_group_search_clause(query.strip())
    if search_clause is not None:
        base = base.filter(search_clause)
    return _apply_visibility_clause(base, visibility_clause)


def list_agency_groups_page(
    db: Session,
    *,
    agency_id: str,
    is_active: bool | None = None,
    query: str = "",
    page: int = 1,
    page_size: int = AGENCY_GROUPS_PAGE_SIZE_DEFAULT,
    visibility_clause=True,
) -> tuple[list[AgencyGroup], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, AGENCY_GROUPS_PAGE_SIZE_MAX))
    base = _agency_groups_filtered_query(
        db,
        agency_id=agency_id,
        is_active=is_active,
        query=query,
        visibility_clause=visibility_clause,
    )
    total = base.count()
    if total == 0:
        return [], 0

    ordered_ids = [
        row[0]
        for row in (
            base.with_entities(AgencyGroup.id)
            .order_by(AgencyGroup.sailing_date.desc(), AgencyGroup.group_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
    ]
    if not ordered_ids:
        return [], total

    groups_by_id = {
        group.id: group
        for group in _groups_query(db, agency_id).filter(AgencyGroup.id.in_(ordered_ids)).all()
    }
    return [groups_by_id[group_id] for group_id in ordered_ids if group_id in groups_by_id], total


def get_agency_group_detail(db: Session, *, agency_id: str, group_id: str) -> AgencyGroup:
    group = _groups_query(db, agency_id).filter(AgencyGroup.id == group_id).first()
    return require_record_for_agency(group, agency_id=agency_id)


def create_agency_group(
    db: Session,
    *,
    agency_id: str,
    group_name: str,
    cruise_line: str,
    ship_name: str,
    sailing_date: date,
    disembarkation_date: date,
    group_id_code: str | None = None,
    group_amenities: str | None = None,
    tc_ratio: str | None = None,
    is_active: bool = True,
    inventory_items: list[dict] | None = None,
    created_by_id: int | None = None,
) -> AgencyGroup:
    inventory_rows = list(inventory_items or [])
    try:
        normalized_line = validate_group_create(
            cruise_line=cruise_line,
            sailing_date=sailing_date,
            disembarkation_date=disembarkation_date,
            tc_ratio=tc_ratio,
            inventory_rows=inventory_rows,
        )
    except AgencyGroupValidationError as exc:
        _raise_validation_error(exc)

    group = AgencyGroup(
        id=_new_id(),
        agency_id=agency_id,
        created_by_id=created_by_id,
        group_name=group_name.strip(),
        cruise_line=normalized_line,
        ship_name=ship_name.strip(),
        sailing_date=sailing_date,
        disembarkation_date=disembarkation_date,
        group_id_code=group_id_code.strip() if group_id_code and group_id_code.strip() else None,
        group_amenities=group_amenities.strip() if group_amenities and group_amenities.strip() else None,
        tc_ratio=normalize_tc_ratio(tc_ratio),
        is_active=is_active,
    )
    db.add(group)
    db.flush()

    for row in inventory_rows:
        inventory = AgencyGroupInventory(
            id=_new_id(),
            group_id=group.id,
            cabin_category=str(row["cabin_category"]).strip(),
            cabin_type=str(row["cabin_type"]).strip(),
            cabin_description=(
                str(row["cabin_description"]).strip()
                if row.get("cabin_description") and str(row["cabin_description"]).strip()
                else None
            ),
            price_per_cabin=row.get("price_per_cabin", 0),
            deposit_per_cabin=row.get("deposit_per_cabin", 0),
            cabins_allocated=int(row.get("cabins_allocated", 0)),
            cabins_reserved=int(row.get("cabins_reserved", 0)),
        )
        db.add(inventory)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A cabin category already exists for this group.",
        ) from exc

    db.refresh(group)
    return get_agency_group_detail(db, agency_id=agency_id, group_id=group.id)


def update_agency_group(
    db: Session,
    *,
    agency_id: str,
    group_id: str,
    updates: dict,
) -> AgencyGroup:
    group = get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)

    try:
        validate_group_update(
            group,
            cruise_line=updates.get("cruise_line"),
            sailing_date=updates.get("sailing_date"),
            disembarkation_date=updates.get("disembarkation_date"),
            tc_ratio=updates.get("tc_ratio"),
        )
    except AgencyGroupValidationError as exc:
        _raise_validation_error(exc)

    if "group_name" in updates and updates["group_name"] is not None:
        group.group_name = updates["group_name"].strip()
    if "cruise_line" in updates and updates["cruise_line"] is not None:
        group.cruise_line = normalize_cruise_line_value(updates["cruise_line"])
    if "ship_name" in updates and updates["ship_name"] is not None:
        group.ship_name = updates["ship_name"].strip()
    if "sailing_date" in updates and updates["sailing_date"] is not None:
        group.sailing_date = updates["sailing_date"]
    if "disembarkation_date" in updates and updates["disembarkation_date"] is not None:
        group.disembarkation_date = updates["disembarkation_date"]
    if "group_id_code" in updates:
        code = updates["group_id_code"]
        group.group_id_code = code.strip() if code and str(code).strip() else None
    if "group_amenities" in updates:
        amenities = updates["group_amenities"]
        group.group_amenities = amenities.strip() if amenities and str(amenities).strip() else None
    if "tc_ratio" in updates:
        group.tc_ratio = normalize_tc_ratio(updates["tc_ratio"])
    if "is_active" in updates and updates["is_active"] is not None:
        group.is_active = bool(updates["is_active"])

    db.commit()
    return get_agency_group_detail(db, agency_id=agency_id, group_id=group.id)


def archive_agency_group(db: Session, *, agency_id: str, group_id: str) -> AgencyGroup:
    return update_agency_group(
        db,
        agency_id=agency_id,
        group_id=group_id,
        updates={"is_active": False},
    )


def create_agency_group_inventory(
    db: Session,
    *,
    agency_id: str,
    group_id: str,
    cabin_category: str,
    cabin_type: str,
    cabin_description: str | None = None,
    price_per_cabin: float = 0,
    deposit_per_cabin: float = 0,
    cabins_allocated: int = 0,
    cabins_reserved: int = 0,
) -> AgencyGroup:
    get_agency_group_for_agency(db, group_id, agency_id)
    row = {
        "cabin_category": cabin_category,
        "cabin_type": cabin_type,
        "cabin_description": cabin_description,
        "price_per_cabin": price_per_cabin,
        "deposit_per_cabin": deposit_per_cabin,
        "cabins_allocated": cabins_allocated,
        "cabins_reserved": cabins_reserved,
    }
    try:
        validate_inventory_row_payload(row)
    except AgencyGroupValidationError as exc:
        _raise_validation_error(exc)

    inventory = AgencyGroupInventory(
        id=_new_id(),
        group_id=group_id,
        cabin_category=str(row["cabin_category"]).strip(),
        cabin_type=row["cabin_type"],
        cabin_description=row.get("cabin_description"),
        price_per_cabin=row["price_per_cabin"],
        deposit_per_cabin=row["deposit_per_cabin"],
        cabins_allocated=row["cabins_allocated"],
        cabins_reserved=row["cabins_reserved"],
    )
    db.add(inventory)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A cabin category already exists for this group.",
        ) from exc

    return get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)


def update_agency_group_inventory(
    db: Session,
    *,
    agency_id: str,
    inventory_id: str,
    updates: dict,
) -> AgencyGroup:
    inventory = get_agency_group_inventory_for_agency(db, inventory_id, agency_id)
    try:
        validate_inventory_update(
            inventory,
            cabins_allocated=updates.get("cabins_allocated"),
            cabins_reserved=updates.get("cabins_reserved"),
            price_per_cabin=updates.get("price_per_cabin"),
            deposit_per_cabin=updates.get("deposit_per_cabin"),
            cabin_type=updates.get("cabin_type"),
        )
    except AgencyGroupValidationError as exc:
        _raise_validation_error(exc)

    if "cabin_category" in updates and updates["cabin_category"] is not None:
        inventory.cabin_category = updates["cabin_category"].strip()
    if "cabin_type" in updates and updates["cabin_type"] is not None:
        next_cabin_type = str(updates["cabin_type"]).strip()
        if next_cabin_type != inventory.cabin_type:
            inventory.cabin_type = validate_cabin_type(next_cabin_type)
    if "cabin_description" in updates:
        description = updates["cabin_description"]
        inventory.cabin_description = description.strip() if description and str(description).strip() else None
    if "price_per_cabin" in updates and updates["price_per_cabin"] is not None:
        inventory.price_per_cabin = updates["price_per_cabin"]
    if "deposit_per_cabin" in updates and updates["deposit_per_cabin"] is not None:
        inventory.deposit_per_cabin = updates["deposit_per_cabin"]
    if "cabins_allocated" in updates and updates["cabins_allocated"] is not None:
        inventory.cabins_allocated = updates["cabins_allocated"]
    if "cabins_reserved" in updates and updates["cabins_reserved"] is not None:
        inventory.cabins_reserved = updates["cabins_reserved"]

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A cabin category already exists for this group.",
        ) from exc

    return get_agency_group_detail(db, agency_id=agency_id, group_id=inventory.group_id)


def delete_agency_group_inventory(
    db: Session,
    *,
    agency_id: str,
    inventory_id: str,
) -> AgencyGroup:
    inventory = get_agency_group_inventory_for_agency(db, inventory_id, agency_id)
    if inventory.cabins_reserved > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove inventory with reserved cabins.",
        )
    group_id = inventory.group_id
    db.delete(inventory)
    db.commit()
    return get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)


def group_picker_item_payload(group: AgencyGroup) -> dict:
    return {
        "id": group.id,
        "group_name": group.group_name,
        "cruise_line": group.cruise_line,
        "ship_name": group.ship_name,
        "sailing_date": group.sailing_date,
        "disembarkation_date": group.disembarkation_date,
    }


def group_intake_summary_payload(group: AgencyGroup) -> dict:
    return {
        "id": group.id,
        "group_name": group.group_name,
        "cruise_line": group.cruise_line,
        "ship_name": group.ship_name,
        "sailing_date": group.sailing_date,
        "disembarkation_date": group.disembarkation_date,
        "group_id_code": group.group_id_code,
        "group_amenities": group.group_amenities,
    }


def format_inventory_option_label(
    *,
    cabin_category: str,
    cabin_type: str,
    cabin_description: str | None,
    price_per_cabin: float,
    cabins_remaining: int,
) -> str:
    description = (cabin_description or cabin_type).strip()
    price_label = f"${price_per_cabin:,.2f}".replace(".00", "")
    return f"{description} ({cabin_category}) - {price_label} [{cabins_remaining} left]"


def list_active_groups_picker(
    db: Session,
    *,
    agency_id: str,
    query: str = "",
    limit: int = AGENCY_GROUPS_PICKER_LIMIT,
    visibility_clause=True,
) -> list[AgencyGroup]:
    normalized_limit = max(1, min(limit, AGENCY_GROUPS_PICKER_LIMIT))
    return (
        _agency_groups_filtered_query(
            db,
            agency_id=agency_id,
            is_active=True,
            query=query,
            visibility_clause=visibility_clause,
        )
        .order_by(AgencyGroup.sailing_date.asc(), AgencyGroup.group_name.asc())
        .limit(normalized_limit)
        .all()
    )


def list_group_inventory_options(
    db: Session,
    *,
    agency_id: str,
    group_id: str,
) -> list[dict]:
    group = get_agency_group_detail(db, agency_id=agency_id, group_id=group_id)
    options: list[dict] = []
    for item in group.inventory_items:
        remaining = compute_cabins_remaining(
            cabins_allocated=item.cabins_allocated,
            cabins_reserved=item.cabins_reserved,
        )
        price = float(item.price_per_cabin)
        deposit = float(item.deposit_per_cabin)
        options.append(
            {
                "id": item.id,
                "cabin_category": item.cabin_category,
                "cabin_type": item.cabin_type,
                "cabin_description": item.cabin_description,
                "price_per_cabin": price,
                "deposit_per_cabin": deposit,
                "cabins_remaining": remaining,
                "label": format_inventory_option_label(
                    cabin_category=item.cabin_category,
                    cabin_type=item.cabin_type,
                    cabin_description=item.cabin_description,
                    price_per_cabin=price,
                    cabins_remaining=remaining,
                ),
                "is_selectable": remaining > 0,
            }
        )
    return options


def validate_travel_request_group_alignment(
    db: Session,
    *,
    agency_id: str,
    group_id: str,
    cruise_lines: list[str],
    ship_name: str | None,
    departure_date: date,
    return_date: date,
) -> AgencyGroup:
    group = get_agency_group_for_agency(db, group_id, agency_id)
    normalized_line = normalize_cruise_line_value(group.cruise_line)
    request_lines = [normalize_cruise_line_value(line) for line in cruise_lines]
    if request_lines != [normalized_line]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cruise line must match the selected group block.",
        )
    if (ship_name or "").strip() != group.ship_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ship name must match the selected group block.",
        )
    if departure_date != group.sailing_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Departure date must match the selected group sailing date.",
        )
    if return_date != group.disembarkation_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Return date must match the selected group disembarkation date.",
        )
    return group


def normalize_group_booking_inputs(
    db: Session,
    *,
    agency_id: str,
    group_id: str,
    bookings: list[dict],
    fallback_inventory_id: str | None = None,
    fallback_cabins_requested: int = 1,
) -> tuple[list[dict], list[str], int]:
    normalized_inputs = bookings
    if not normalized_inputs and fallback_inventory_id:
        normalized_inputs = [
            {
                "group_inventory_id": fallback_inventory_id,
                "cabins_requested": fallback_cabins_requested,
            }
        ]
    if not normalized_inputs:
        return [], [], 0

    seen_inventory_ids: set[str] = set()
    normalized_rows: list[dict] = []
    cabin_types: list[str] = []
    total_cabins = 0

    for row in normalized_inputs:
        inventory_id = str(row["group_inventory_id"]).strip()
        cabins_requested = int(row["cabins_requested"])
        if inventory_id in seen_inventory_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate inventory category selected for this request.",
            )
        seen_inventory_ids.add(inventory_id)
        if cabins_requested < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each inventory selection must request at least one cabin.",
            )

        inventory = get_agency_group_inventory_for_agency(db, inventory_id, agency_id)
        if inventory.group_id != group_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group inventory does not belong to the selected group.",
            )
        remaining = compute_cabins_remaining(
            cabins_allocated=inventory.cabins_allocated,
            cabins_reserved=inventory.cabins_reserved,
        )
        if cabins_requested > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only {remaining} cabins remain for {inventory.cabin_category}.",
            )
        if inventory.cabin_type not in CABIN_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory cabin type '{inventory.cabin_type}' is not supported on requests.",
            )

        normalized_rows.append(
            {
                "group_inventory_id": inventory_id,
                "cabins_requested": cabins_requested,
                "inventory": inventory,
            }
        )
        cabin_types.append(inventory.cabin_type)
        total_cabins += cabins_requested

    return normalized_rows, cabin_types, total_cabins


def group_booking_read_payload(booking: TravelRequestGroupBooking) -> dict:
    inventory = booking.group_inventory
    remaining = compute_cabins_remaining(
        cabins_allocated=inventory.cabins_allocated,
        cabins_reserved=inventory.cabins_reserved,
    )
    return {
        "id": booking.id,
        "group_inventory_id": booking.group_inventory_id,
        "cabins_requested": booking.cabins_requested,
        "cabin_category": inventory.cabin_category,
        "cabin_type": inventory.cabin_type,
        "cabin_description": inventory.cabin_description,
        "price_per_cabin": float(inventory.price_per_cabin),
        "deposit_per_cabin": float(inventory.deposit_per_cabin),
        "cabins_remaining": remaining,
    }


def replace_travel_request_group_bookings(
    db: Session,
    *,
    request: TravelRequest,
    booking_rows: list[dict],
) -> None:
    request.group_bookings.clear()
    db.flush()
    for row in booking_rows:
        request.group_bookings.append(
            TravelRequestGroupBooking(
                id=_new_id(),
                travel_request_id=request.id,
                group_inventory_id=row["group_inventory_id"],
                cabins_requested=row["cabins_requested"],
            )
        )
