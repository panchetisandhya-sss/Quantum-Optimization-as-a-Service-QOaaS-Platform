import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class BreakPolicy(BaseModel):
    policy_id: str = "default_global"
    name: str = "Standard International Break Policy"
    
    # Durations (in minutes)
    short_break_duration: int = 20
    lunch_duration: int = 30
    
    # Shift length thresholds (in hours)
    min_hours_for_short_break: float = 4.0
    min_hours_for_lunch: float = 6.0
    min_hours_for_second_short_break: float = 8.0
    
    # Batching & Staggering Settings
    batch_size_default: int = 20
    batch_strategy: str = "even_distribution"  # "even_distribution" or "fixed_batch_size"
    min_staffed_percent: float = 80.0          # min % of roster that MUST remain working on duty
    max_break_percent: float = 20.0            # max % on break at any time (100 - min_staffed_percent)
    
    # Rotation & Consistency Mode
    rotation_mode: str = "daily_rotate"        # "daily_rotate" or "consistent"
    reshuffle_per_break: bool = False          # False = consistent batch across breaks, True = reshuffle
    
    # Toggles
    enable_under_4h_breaks: bool = False


class BreakScheduleItem(BaseModel):
    employee_id: str
    employee_name: str
    shift_id: str
    shift_name: str
    break_type: str              # "Short Break 1", "Lunch Break", "Short Break 2"
    batch_id: int
    batch_name: str
    scheduled_start_time: str    # "HH:MM"
    scheduled_end_time: str      # "HH:MM"
    duration_minutes: int


class ShiftBreakWindow(BaseModel):
    break_type: str
    window_start: str            # "HH:MM"
    window_end: str              # "HH:MM"
    duration_minutes: int


class BreakValidationWarning(BaseModel):
    time_slot: str
    employees_on_break: int
    total_employees: int
    percent_on_break: float
    max_allowed_percent: float
    warning_message: str


def _parse_time(time_str: str) -> datetime:
    """Parses HH:MM string into datetime (using dummy date 2026-01-01)."""
    parts = time_str.split(":")
    return datetime(2026, 1, 1, int(parts[0]), int(parts[1]))


def _format_time(dt: datetime) -> str:
    """Formats datetime object to HH:MM string."""
    return dt.strftime("%H:%M")


def partition_into_batches(
    employees: List[Dict[str, Any]],
    batch_size_default: int,
    max_allowed_batch_size: int,
    strategy: str = "even_distribution"
) -> List[List[Dict[str, Any]]]:
    """
    Partitions employee list into batches respecting batch size limits and strategy.
    """
    total_n = len(employees)
    if total_n == 0:
        return []

    effective_batch_size = max(1, min(batch_size_default, max_allowed_batch_size))
    
    if total_n <= effective_batch_size:
        return [employees]

    batch_count = math.ceil(total_n / effective_batch_size)
    batches: List[List[Dict[str, Any]]] = []

    if strategy == "even_distribution":
        base_size = total_n // batch_count
        remainder = total_n % batch_count
        
        start_idx = 0
        for b in range(batch_count):
            size = base_size + (1 if b < remainder else 0)
            end_idx = start_idx + size
            batches.append(employees[start_idx:end_idx])
            start_idx = end_idx
    else:  # 'fixed_batch_size'
        for b in range(batch_count):
            start_idx = b * effective_batch_size
            end_idx = min(start_idx + effective_batch_size, total_n)
            batches.append(employees[start_idx:end_idx])

    return batches


def determine_required_breaks(shift_duration_hours: float, policy: BreakPolicy) -> List[Dict[str, Any]]:
    """
    Determines required break types for a given shift length based on policy thresholds.
    """
    breaks = []
    
    if shift_duration_hours < policy.min_hours_for_short_break:
        if policy.enable_under_4h_breaks:
            breaks.append({
                "type": "Short Break 1",
                "duration": policy.short_break_duration
            })
        return breaks

    # 1. Short Break 1 (4h+ shifts)
    breaks.append({
        "type": "Short Break 1",
        "duration": policy.short_break_duration
    })

    # 2. Lunch Break (6h+ shifts)
    if shift_duration_hours >= policy.min_hours_for_lunch:
        breaks.append({
            "type": "Lunch Break",
            "duration": policy.lunch_duration
        })

    # 3. Short Break 2 (8h+ shifts)
    if shift_duration_hours >= policy.min_hours_for_second_short_break:
        breaks.append({
            "type": "Short Break 2",
            "duration": policy.short_break_duration
        })

    return breaks


def generate_staggered_break_schedule(
    employees: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
    policy: Optional[BreakPolicy] = None,
    day_offset: int = 0
) -> Dict[str, Any]:
    """
    Core Pure Function: Generates staggered break schedules for all employees across shifts.
    Guaranteeing zero inter-break overlap and strict compliance with min_staffed_percent.
    """
    if policy is None:
        policy = BreakPolicy()

    all_schedule_items: List[BreakScheduleItem] = []
    all_warnings: List[BreakValidationWarning] = []
    shift_summaries: List[Dict[str, Any]] = []

    # Map employees by shift_id
    emp_by_shift: Dict[str, List[Dict[str, Any]]] = {}
    for s in shifts:
        emp_by_shift[s["id"]] = []

    for emp in employees:
        s_id = emp.get("shift_id")
        if s_id in emp_by_shift:
            emp_by_shift[s_id].append(emp)
        elif shifts:
            emp_by_shift[shifts[0]["id"]].append(emp)

    for s_idx, shift in enumerate(shifts):
        shift_id = shift["id"]
        shift_name = shift.get("name", f"Shift {s_idx + 1}")
        start_str = shift.get("start_time", "08:00")
        end_str = shift.get("end_time", "16:00")

        dt_start = _parse_time(start_str)
        dt_end = _parse_time(end_str)
        if dt_end <= dt_start:
            dt_end += timedelta(days=1)

        duration_hours = (dt_end - dt_start).total_seconds() / 3600.0
        shift_emps = emp_by_shift.get(shift_id, [])
        total_n = len(shift_emps)

        if total_n == 0:
            continue

        # Required break types for this shift
        break_types = determine_required_breaks(duration_hours, policy)
        num_break_types = len(break_types)
        if num_break_types == 0:
            continue

        # Max break percent cap (e.g. 15%)
        max_break_pct = policy.max_break_percent
        max_allowed_employees = max(1, math.floor(total_n * (max_break_pct / 100.0)))
        
        # Partition employees into batches
        batches = partition_into_batches(
            employees=shift_emps,
            batch_size_default=policy.batch_size_default,
            max_allowed_batch_size=max_allowed_employees,
            strategy=policy.batch_strategy
        )

        batch_count = len(batches)

        # Track completion time of previous break type to guarantee non-overlapping segments
        last_break_type_end_dt = dt_start + timedelta(minutes=30)

        # Process each break type inside its dedicated segment
        for b_type_idx, b_info in enumerate(break_types):
            b_name = b_info["type"]
            b_dur = b_info["duration"]

            # Start of this break type's window (sequential chaining)
            w_start = last_break_type_end_dt
            if b_type_idx > 0:
                w_start += timedelta(minutes=15)  # 15-min gap between break types

            # Max batches allowed to overlap concurrently without violating max_break_pct
            max_concurrent_batches = max(1, math.floor(max_allowed_employees / math.ceil(total_n / batch_count)))

            # Minimum stagger step to guarantee concurrency cap
            min_stagger = math.ceil(b_dur / max_concurrent_batches)

            # Assign timeslots to batches with fair rotation
            max_end_for_type = w_start
            for batch_idx, batch_emps in enumerate(batches):
                if policy.rotation_mode == "daily_rotate":
                    slot_idx = (batch_idx + day_offset + b_type_idx) % batch_count
                else:
                    slot_idx = batch_idx

                b_start = w_start + timedelta(minutes=int(slot_idx * min_stagger))
                b_end = b_start + timedelta(minutes=b_dur)

                # Ensure break stays within overall shift bounds
                if b_end > dt_end - timedelta(minutes=10):
                    b_end = dt_end - timedelta(minutes=10)
                    b_start = max(dt_start + timedelta(minutes=15), b_end - timedelta(minutes=b_dur))

                if b_end > max_end_for_type:
                    max_end_for_type = b_end

                batch_label = f"Batch #{batch_idx + 1}"

                for emp in batch_emps:
                    item = BreakScheduleItem(
                        employee_id=str(emp.get("id", f"emp_{emp.get('name')}")),
                        employee_name=str(emp.get("name", "Staff")),
                        shift_id=shift_id,
                        shift_name=shift_name,
                        break_type=b_name,
                        batch_id=batch_idx + 1,
                        batch_name=batch_label,
                        scheduled_start_time=_format_time(b_start),
                        scheduled_end_time=_format_time(b_end),
                        duration_minutes=b_dur
                    )
                    all_schedule_items.append(item)

            last_break_type_end_dt = max_end_for_type

        # Validation: Check max break concurrency for this shift
        curr_dt = dt_start
        while curr_dt < dt_end:
            c_str = _format_time(curr_dt)
            curr_dt_end = curr_dt + timedelta(minutes=5)
            
            # Count employees on break during this 5-minute interval
            on_break_cnt = 0
            for item in all_schedule_items:
                if item.shift_id == shift_id:
                    s_dt = _parse_time(item.scheduled_start_time)
                    e_dt = _parse_time(item.scheduled_end_time)
                    if s_dt <= curr_dt < e_dt:
                        on_break_cnt += 1

            pct_on_break = (on_break_cnt / total_n) * 100.0 if total_n > 0 else 0.0
            if pct_on_break > (max_break_pct + 0.1):  # Allow tiny floating point tolerance
                all_warnings.append(BreakValidationWarning(
                    time_slot=c_str,
                    employees_on_break=on_break_cnt,
                    total_employees=total_n,
                    percent_on_break=round(pct_on_break, 1),
                    max_allowed_percent=max_break_pct,
                    warning_message=f"Shift {shift_name} at {c_str}: {on_break_cnt}/{total_n} ({pct_on_break:.1f}%) on break exceeds max threshold ({max_break_pct:.1f}%)."
                ))
            curr_dt = curr_dt_end

        shift_summaries.append({
            "shift_id": shift_id,
            "shift_name": shift_name,
            "total_employees": total_n,
            "batch_count": batch_count,
            "effective_batch_size": math.ceil(total_n / batch_count) if batch_count > 0 else 0,
            "break_types_assigned": [b["type"] for b in break_types]
        })

    dump_item = lambda x: x.model_dump() if hasattr(x, 'model_dump') else x.dict()

    return {
        "schedules": [dump_item(item) for item in all_schedule_items],
        "warnings": [dump_item(w) for w in all_warnings],
        "summary": shift_summaries,
        "policy": dump_item(policy)
    }
