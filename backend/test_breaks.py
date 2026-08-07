import pytest
from app.services.breaks import (
    BreakPolicy,
    generate_staggered_break_schedule,
    partition_into_batches,
    determine_required_breaks,
)

def test_determine_required_breaks():
    policy = BreakPolicy()
    
    # < 4 hours => 0 breaks
    assert len(determine_required_breaks(3.5, policy)) == 0

    # 4-6 hours => 1 short break
    b_4h = determine_required_breaks(5.0, policy)
    assert len(b_4h) == 1
    assert b_4h[0]["type"] == "Short Break 1"

    # 6-8 hours => 1 short break + 1 lunch
    b_7h = determine_required_breaks(7.0, policy)
    assert len(b_7h) == 2
    assert [b["type"] for b in b_7h] == ["Short Break 1", "Lunch Break"]

    # > 8 hours => 2 short breaks + 1 lunch
    b_9h = determine_required_breaks(9.0, policy)
    assert len(b_9h) == 3
    assert [b["type"] for b in b_9h] == ["Short Break 1", "Lunch Break", "Short Break 2"]


def test_even_division():
    # 200 employees, batch size 20 => 10 batches of 20
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(200)]
    shifts = [{"id": "s1", "name": "Morning Shift", "start_time": "08:00", "end_time": "16:00"}]
    policy = BreakPolicy(batch_size_default=20, batch_strategy="even_distribution")

    result = generate_staggered_break_schedule(employees, shifts, policy)
    schedules = result["schedules"]

    assert len(schedules) > 0
    assert result["summary"][0]["batch_count"] == 10
    assert result["summary"][0]["effective_batch_size"] == 20
    assert len(result["warnings"]) == 0


def test_odd_division_rebalance():
    # 205 employees, batch size 20 => 11 batches of ~18-19 each
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(205)]
    shifts = [{"id": "s1", "name": "Morning Shift", "start_time": "08:00", "end_time": "16:00"}]
    
    batches = partition_into_batches(employees, batch_size_default=20, max_allowed_batch_size=30, strategy="even_distribution")
    assert len(batches) == 11
    sizes = [len(b) for b in batches]
    assert max(sizes) - min(sizes) <= 1
    assert sum(sizes) == 205


def test_very_small_team():
    # 3 employees => 3 individual batches of 1
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(3)]
    shifts = [{"id": "s1", "name": "Morning Shift", "start_time": "08:00", "end_time": "16:00"}]
    policy = BreakPolicy(batch_size_default=20)

    result = generate_staggered_break_schedule(employees, shifts, policy)
    schedules = result["schedules"]

    assert len(schedules) > 0
    assert result["summary"][0]["batch_count"] == 3
    # Check that each employee gets distinct staggered start times for lunch
    lunch_items = [s for s in schedules if s["break_type"] == "Lunch Break"]
    start_times = set(item["scheduled_start_time"] for item in lunch_items)
    assert len(start_times) == 3


def test_very_large_team():
    # 1200 employees => 60 batches of 20
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(1200)]
    shifts = [{"id": "s1", "name": "Day Shift", "start_time": "08:00", "end_time": "17:00"}]
    policy = BreakPolicy(batch_size_default=20, min_staffed_percent=85.0)

    result = generate_staggered_break_schedule(employees, shifts, policy)
    assert len(result["schedules"]) == 1200 * 3  # 3 breaks per employee for 9h shift
    assert result["summary"][0]["total_employees"] == 1200


def test_min_staffed_percent_constraint():
    # 100 employees, policy min_staffed_percent = 90% (max 10% on break = max 10 employees/batch)
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(100)]
    shifts = [{"id": "s1", "name": "Standard Shift", "start_time": "08:00", "end_time": "16:00"}]
    
    # Try requesting batch_size_default = 50, but max allowed is 10
    policy = BreakPolicy(batch_size_default=50, min_staffed_percent=90.0, max_break_percent=10.0)
    
    result = generate_staggered_break_schedule(employees, shifts, policy)
    assert result["summary"][0]["effective_batch_size"] <= 10
    assert result["summary"][0]["batch_count"] >= 10


def test_fair_rotation():
    employees = [{"id": f"emp_{i}", "name": f"Employee {i+1}", "shift_id": "s1"} for i in range(20)]
    shifts = [{"id": "s1", "name": "Day Shift", "start_time": "08:00", "end_time": "16:00"}]
    policy = BreakPolicy(batch_size_default=5, rotation_mode="daily_rotate")

    res_day0 = generate_staggered_break_schedule(employees, shifts, policy, day_offset=0)
    res_day1 = generate_staggered_break_schedule(employees, shifts, policy, day_offset=1)

    lunch_d0 = res_day0["schedules"][0]["scheduled_start_time"]
    lunch_d1 = res_day1["schedules"][0]["scheduled_start_time"]
    
    # Timeslots should rotate between Day 0 and Day 1
    assert lunch_d0 != lunch_d1
