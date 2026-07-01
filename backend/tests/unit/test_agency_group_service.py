from datetime import date

import pytest
from fastapi import HTTPException

from app.models import AgencyGroup, AgencyGroupInventory
from app.services.agency_group_seed import SEED_GROUP_NAME, seed_agency_groups
from app.services.agency_group_service import (
    AgencyGroupValidationError,
    compute_cabins_remaining,
    get_agency_group_for_agency,
    group_summary_rollups,
    list_agency_groups_page,
    validate_group_create,
    validate_group_dates,
    validate_inventory_counts,
    validate_inventory_update,
    validate_travel_request_group_linkage,
)
from app.tenant_constants import DEFAULT_AGENCY_ID


GROUP_ID = "11111111-1111-4111-8111-111111111101"
INVENTORY_ID = "22222222-2222-4222-8222-222222222201"
INVENTORY_ID_2 = "22222222-2222-4222-8222-222222222202"
OTHER_GROUP_ID = "33333333-3333-4333-8333-333333333301"


def _make_group(db, *, is_active: bool = True) -> AgencyGroup:
    group = AgencyGroup(
        id=GROUP_ID,
        agency_id=DEFAULT_AGENCY_ID,
        group_name="Test Block",
        cruise_line="Royal Caribbean International",
        ship_name="Oasis of the Seas",
        sailing_date=date(2027, 4, 1),
        disembarkation_date=date(2027, 4, 8),
        group_id_code="TEST-001",
        tc_ratio="1:16",
        is_active=is_active,
    )
    db.add(group)
    db.flush()
    return group


def _make_inventory(db, group: AgencyGroup, *, allocated: int = 10, reserved: int = 2) -> AgencyGroupInventory:
    inventory = AgencyGroupInventory(
        id=INVENTORY_ID,
        group_id=group.id,
        cabin_category="8C",
        cabin_type="Balcony",
        price_per_cabin=1200,
        cabins_allocated=allocated,
        cabins_reserved=reserved,
    )
    db.add(inventory)
    db.flush()
    return inventory


def test_validate_group_dates_rejects_disembarkation_before_sailing():
    with pytest.raises(AgencyGroupValidationError):
        validate_group_dates(sailing_date=date(2027, 4, 10), disembarkation_date=date(2027, 4, 1))


def test_validate_inventory_counts_rejects_reserved_above_allocated():
    with pytest.raises(AgencyGroupValidationError):
        validate_inventory_counts(cabins_allocated=5, cabins_reserved=6)


def test_validate_group_create_normalizes_cruise_line():
    normalized = validate_group_create(
        cruise_line="royal caribbean",
        sailing_date=date(2027, 4, 1),
        disembarkation_date=date(2027, 4, 8),
        inventory_rows=[{"cabin_type": "Balcony", "cabins_allocated": 4, "cabins_reserved": 0}],
    )
    assert normalized == "Royal Caribbean International"


def test_compute_cabins_remaining_and_group_summary_rollups(db):
    group = _make_group(db)
    _make_inventory(db, group, allocated=10, reserved=3)
    db.add(
        AgencyGroupInventory(
            id=INVENTORY_ID_2,
            group_id=group.id,
            cabin_category="4D",
            cabin_type="Inside",
            price_per_cabin=800,
            cabins_allocated=6,
            cabins_reserved=1,
        )
    )
    db.flush()
    db.refresh(group)

    assert compute_cabins_remaining(cabins_allocated=10, cabins_reserved=3) == 7
    summary = group_summary_rollups(group)
    assert summary["inventory_row_count"] == 2
    assert summary["total_cabins_allocated"] == 16
    assert summary["total_cabins_reserved"] == 4
    assert summary["total_cabins_remaining"] == 12


def test_validate_inventory_update_blocks_reducing_allocated_below_reserved(db):
    group = _make_group(db)
    inventory = _make_inventory(db, group, allocated=10, reserved=8)
    with pytest.raises(AgencyGroupValidationError):
        validate_inventory_update(inventory, cabins_allocated=5)


def test_validate_inventory_update_allows_deposit_change_for_legacy_cabin_type(db):
    group = _make_group(db)
    inventory = _make_inventory(db, group)
    inventory.cabin_type = "Inside"
    validate_inventory_update(inventory, deposit_per_cabin=250)
    validate_inventory_update(inventory, cabin_type="Inside", deposit_per_cabin=300)


def test_validate_inventory_update_rejects_changing_to_invalid_cabin_type(db):
    group = _make_group(db)
    inventory = _make_inventory(db, group)
    inventory.cabin_type = "Inside"
    with pytest.raises(AgencyGroupValidationError):
        validate_inventory_update(inventory, cabin_type="Penthouse")


def test_get_agency_group_for_agency_enforces_tenant_isolation(db):
    group = _make_group(db)
    loaded = get_agency_group_for_agency(db, group.id, DEFAULT_AGENCY_ID)
    assert loaded.id == group.id

    with pytest.raises(HTTPException) as exc:
        get_agency_group_for_agency(db, group.id, "other-agency-id")
    assert exc.value.status_code == 404


def test_validate_travel_request_group_linkage_requires_matching_inventory(db):
    group = _make_group(db)
    inventory = _make_inventory(db, group)

    validate_travel_request_group_linkage(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        group_id=group.id,
        group_inventory_id=inventory.id,
    )

    with pytest.raises(HTTPException) as exc:
        validate_travel_request_group_linkage(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            group_id=group.id,
            group_inventory_id="99999999-9999-4999-8999-999999999901",
        )
    assert exc.value.status_code == 404

    other_group = AgencyGroup(
        id=OTHER_GROUP_ID,
        agency_id=DEFAULT_AGENCY_ID,
        group_name="Other Block",
        cruise_line="Celebrity Cruises",
        ship_name="Ascent",
        sailing_date=date(2027, 5, 1),
        disembarkation_date=date(2027, 5, 8),
        is_active=True,
    )
    db.add(other_group)
    db.flush()

    with pytest.raises(HTTPException) as exc:
        validate_travel_request_group_linkage(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            group_id=other_group.id,
            group_inventory_id=inventory.id,
        )
    assert exc.value.status_code == 400


def test_validate_travel_request_group_linkage_rejects_inactive_group(db):
    group = _make_group(db, is_active=False)
    with pytest.raises(HTTPException) as exc:
        validate_travel_request_group_linkage(
            db,
            agency_id=DEFAULT_AGENCY_ID,
            group_id=group.id,
            group_inventory_id=None,
        )
    assert exc.value.status_code == 400


def test_seed_agency_groups_is_idempotent(db):
    first = seed_agency_groups(db, DEFAULT_AGENCY_ID)
    second = seed_agency_groups(db, DEFAULT_AGENCY_ID)
    assert first is not None
    assert second is not None
    assert first.id == second.id

    groups = (
        db.query(AgencyGroup)
        .filter(
            AgencyGroup.agency_id == DEFAULT_AGENCY_ID,
            AgencyGroup.group_name == SEED_GROUP_NAME,
        )
        .all()
    )
    assert len(groups) == 1
    assert len(groups[0].inventory_items) == 3


def test_list_agency_groups_page_search_and_pagination(db):
    for index in range(8):
        group = AgencyGroup(
            id=f"44444444-4444-4444-8444-44444444440{index}",
            agency_id=DEFAULT_AGENCY_ID,
            group_name=f"Paged Block {index}",
            cruise_line="Royal Caribbean International",
            ship_name=f"Paged Ship {index}",
            sailing_date=date(2027, 5, index + 1),
            disembarkation_date=date(2027, 5, index + 8),
            group_id_code=f"PAGE-{index:03d}",
            is_active=True,
        )
        db.add(group)
    db.commit()

    page_one, total = list_agency_groups_page(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        is_active=True,
        page=1,
        page_size=7,
    )
    assert total >= 8
    assert len(page_one) == 7

    search_results, search_total = list_agency_groups_page(
        db,
        agency_id=DEFAULT_AGENCY_ID,
        is_active=True,
        query="PAGE-003",
        page=1,
        page_size=7,
    )
    assert search_total == 1
    assert search_results[0].ship_name == "Paged Ship 3"
