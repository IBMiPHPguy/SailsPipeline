from app.group_tc import compute_tc_progress
from app.services.agency_group_metrics_service import (
    build_agency_group_metrics,
    liquidation_percent,
    liquidation_tone,
)


def test_liquidation_tone_thresholds():
    assert liquidation_tone(allocated=10, reserved=0, remaining=10) == "healthy"
    assert liquidation_tone(allocated=10, reserved=8, remaining=2) == "nearing_sellout"
    assert liquidation_tone(allocated=10, reserved=10, remaining=0) == "sold_out"


def test_liquidation_percent_clamps_to_hundred():
    assert liquidation_percent(allocated=4, reserved=4) == 100.0
    assert liquidation_percent(allocated=0, reserved=0) == 0.0


def test_build_agency_group_metrics_aggregates_inventory(db):
    from tests.unit.test_agency_group_service import _make_group, _make_inventory

    group = _make_group(db)
    _make_inventory(db, group, allocated=10, reserved=3)
    db.commit()

    metrics = build_agency_group_metrics(db, agency_id=group.agency_id, group_id=group.id)

    assert metrics["totals"]["cabins_allocated"] == 10
    assert metrics["totals"]["cabins_reserved"] == 3
    assert metrics["totals"]["max_gross_yield"] == 12000.0
    assert metrics["totals"]["accrued_gross_yield"] == 3600.0
    assert metrics["totals"]["remaining_gross_yield"] == 8400.0
    assert len(metrics["inventory_rows"]) == 1
    assert metrics["tour_conductor"]["berths_per_credit"] == 16
