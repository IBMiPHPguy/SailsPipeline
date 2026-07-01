from app.group_tc import (
    berths_from_group_cabins,
    compute_tc_progress,
    format_tc_progress_message,
    parse_tc_ratio,
)


def test_parse_tc_ratio_accepts_common_formats():
    assert parse_tc_ratio("1:16").berths_per_credit == 16
    assert parse_tc_ratio(" 1 : 8 ").berths_per_credit == 8
    assert parse_tc_ratio("1:8").used_default is False


def test_parse_tc_ratio_falls_back_to_default_for_invalid_values():
    parsed = parse_tc_ratio("invalid")
    assert parsed.berths_per_credit == 16
    assert parsed.used_default is True


def test_berths_from_group_cabins_counts_two_per_cabin():
    assert berths_from_group_cabins(0) == 0
    assert berths_from_group_cabins(1) == 2
    assert berths_from_group_cabins(8) == 16


def test_compute_tc_progress_for_four_cabins_reserved():
    progress = compute_tc_progress(total_cabins_reserved=4, tc_ratio="1:16")
    assert progress.total_berths_reserved == 8
    assert progress.tc_credits_earned == 0
    assert progress.berths_until_next_tc == 8
    assert "8 more berths" in format_tc_progress_message(progress)


def test_compute_tc_progress_for_eight_cabins_earns_credit_at_one_to_sixteen():
    progress = compute_tc_progress(total_cabins_reserved=8, tc_ratio="1:16")
    assert progress.total_berths_reserved == 16
    assert progress.tc_credits_earned == 1
    assert progress.berths_until_next_tc == 16
    message = format_tc_progress_message(progress)
    assert "16 berths counted" in message
    assert "1 Tour Conductor credit earned" in message
