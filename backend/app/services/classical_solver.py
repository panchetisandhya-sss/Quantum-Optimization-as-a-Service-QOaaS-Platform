"""
services/classical_solver.py — Phase 2: Classical/AI solver for bulk low-complexity clusters.

Used for the majority of clusters in large (30,000+ employee) workforces where
routing every sub-problem through the quantum simulator would be impractical.

Solver priority:
  1. OR-Tools CP-SAT (constraint programming — fast, exact for typical sizes)
  2. Greedy repair fallback (if OR-Tools is unavailable)

Results are returned in the same format as repair_staffing_schedule() so they
can be merged seamlessly with quantum-solved cluster results.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import OR-Tools (optional dependency)
HAS_ORTOOLS = False
try:
    from ortools.sat.python import cp_model  # type: ignore
    HAS_ORTOOLS = True
except ImportError:
    logger.warning(
        "OR-Tools not installed. Classical solver will use greedy fallback. "
        "Install with: pip install ortools"
    )

# Job timeout for OR-Tools solver in seconds
ORTOOLS_TIMEOUT_SECONDS: int = 30


def solve_cluster_classical(
    cluster: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Solve a single staffing cluster using OR-Tools CP-SAT or greedy fallback.

    Args:
        cluster: dict with keys "employees" and "shifts" (same format as modeling.py output)

    Returns:
        A dict compatible with repair_staffing_schedule() output:
          {
            "schedule": List[shift_result_dict],
            "unassigned_employees": List[str],
            "labor_cost": float,
            "confidence_score": float,
            "unassigned_shifts_count": int,
            "solver_used": str,          # extra field — which engine ran
          }
    """
    employees = cluster.get("employees", [])
    shifts = cluster.get("shifts", [])

    if not employees or not shifts:
        return _empty_result(shifts)

    if HAS_ORTOOLS:
        try:
            return _solve_ortools(employees, shifts)
        except Exception as exc:
            logger.error(f"OR-Tools solver failed: {exc}. Falling back to greedy.")

    return _solve_greedy(employees, shifts)


# ---------------------------------------------------------------------------
# OR-Tools CP-SAT implementation
# ---------------------------------------------------------------------------

def _solve_ortools(
    employees: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Formulate and solve the shift assignment problem with OR-Tools CP-SAT.

    Constraints modelled:
      - x[e][s] = 1 only if employee e is available for shift s
      - Each employee assigned to at most 1 shift (max-shift constraint)
      - sum(x[e][s] for e) >= demand[s] for each shift (demand coverage)

    Objective: minimise total labour cost = sum(hourly_rate[e] * 8h * x[e][s])
    """
    model = cp_model.CpModel()

    emp_ids = [e["id"] for e in employees]
    shift_ids = [s["id"] for s in shifts]
    shift_by_id = {s["id"]: s for s in shifts}
    emp_by_id = {e["id"]: e for e in employees}

    # Decision variables x[emp_id][shift_id] ∈ {0, 1}
    x: Dict[Tuple[str, str], Any] = {}
    for e in employees:
        e_health = e.get("health_condition", "Fit").lower()
        e_zone = str(e.get("address", "")).lower()
        for s in shifts:
            s_name = s.get("name", "").lower()
            s_id = s.get("id", "").lower()
            s_zone = str(s.get("zone", "")).lower()

            # Health Safety Rule: Night shift restricted for Night Ineligible / Sensitive / Chronic
            is_night = "night" in s_name or "night" in s_id or "00:00" in s_name or "24:00" in s_name
            if is_night and ("ineligible" in e_health or "sensitive" in e_health or "chronic" in e_health):
                continue  # Health safety constraint: forbid assignment to Night Shift

            if s["id"] in e.get("availability", []):
                x[(e["id"], s["id"])] = model.NewBoolVar(f"x_{e['id']}_{s['id']}")

    # Constraint: max 1 shift per employee
    for e in employees:
        assigned_vars = [x[(e["id"], s["id"])] for s in shifts if (e["id"], s["id"]) in x]
        if assigned_vars:
            model.Add(sum(assigned_vars) <= 1)

    # Constraint: meet shift demand (soft — penalised if impossible)
    # We use slack variables so the model is always feasible
    slack: Dict[str, Any] = {}
    for s in shifts:
        demand = s.get("demand", 1)
        assigned_vars = [x[(e["id"], s["id"])] for e in employees if (e["id"], s["id"]) in x]
        slack_var = model.NewIntVar(0, max(demand, len(employees)), f"slack_{s['id']}")
        slack[s["id"]] = slack_var
        if assigned_vars:
            model.Add(sum(assigned_vars) + slack_var >= demand)
        else:
            model.Add(slack_var >= demand)

    # Objective: minimise cost + heavy penalty for unmet demand
    SLACK_PENALTY = 10_000_000  # penalty per unmet demand slot (ensures staff are assigned first)
    cost_terms = []
    for (eid, sid), var in x.items():
        rate = emp_by_id[eid].get("hourly_rate", 25.0)
        cost_terms.append(int(rate * 8 * 100) * var)  # scale to int (cents)

    slack_penalty_terms = [SLACK_PENALTY * slack[s["id"]] for s in shifts]
    model.Minimize(sum(cost_terms) + sum(slack_penalty_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = ORTOOLS_TIMEOUT_SECONDS
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        logger.warning("OR-Tools CP-SAT did not find a feasible solution. Falling back to greedy.")
        return _solve_greedy(employees, shifts)

    # Extract assignments
    shift_assignments: Dict[str, List[str]] = {s["id"]: [] for s in shifts}
    employee_assigned: Dict[str, bool] = {e["id"]: False for e in employees}
    total_labor_cost = 0.0

    for (eid, sid), var in x.items():
        if solver.Value(var) == 1:
            shift_assignments[sid].append(eid)
            employee_assigned[eid] = True
            total_labor_cost += emp_by_id[eid].get("hourly_rate", 25.0) * 8.0

    return _format_results(
        employees, shifts, shift_assignments, employee_assigned, total_labor_cost,
        solver_used="OR-Tools CP-SAT",
    )


# ---------------------------------------------------------------------------
# Greedy repair fallback
# ---------------------------------------------------------------------------

def _solve_greedy(
    employees: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Simple greedy assignment: for each shift (sorted by demand desc),
    assign cheapest available unassigned employees.
    """
    shift_assignments: Dict[str, List[str]] = {s["id"]: [] for s in shifts}
    employee_assigned: Dict[str, bool] = {e["id"]: False for e in employees}
    total_labor_cost = 0.0
    emp_by_id = {e["id"]: e for e in employees}

    # Sort shifts by demand descending (fill hardest shifts first)
    sorted_shifts = sorted(shifts, key=lambda s: s.get("demand", 1), reverse=True)

    for shift in sorted_shifts:
        sid = shift["id"]
        demand = shift.get("demand", 1)
        s_name = shift.get("name", "").lower()
        s_id = sid.lower()
        is_night = "night" in s_name or "night" in s_id or "00:00" in s_name or "24:00" in s_name

        # Filter candidates by availability AND health safety rules
        eligible = []
        for e in employees:
            if employee_assigned[e["id"]]:
                continue
            if sid not in e.get("availability", []):
                continue
            e_health = e.get("health_condition", "Fit").lower()
            if is_night and ("ineligible" in e_health or "sensitive" in e_health or "chronic" in e_health):
                continue  # Health constraint
            eligible.append(e)

        # Sort eligible candidates: prefer address zone match first, then cheapest rate
        s_zone = str(shift.get("zone", "")).lower()
        candidates = sorted(
            eligible,
            key=lambda e: (0 if s_zone and s_zone in str(e.get("address", "")).lower() else 1, e.get("hourly_rate", 25.0)),
        )

        for emp in candidates[:demand]:
            shift_assignments[sid].append(emp["id"])
            employee_assigned[emp["id"]] = True
            total_labor_cost += emp.get("hourly_rate", 25.0) * 8.0

    return _format_results(
        employees, shifts, shift_assignments, employee_assigned, total_labor_cost,
        solver_used="Greedy Classical Fallback",
    )


# ---------------------------------------------------------------------------
# Shared result formatter
# ---------------------------------------------------------------------------

def _format_results(
    employees: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
    shift_assignments: Dict[str, List[str]],
    employee_assigned: Dict[str, bool],
    total_labor_cost: float,
    solver_used: str,
) -> Dict[str, Any]:
    emp_by_id = {e["id"]: e for e in employees}
    formatted_schedule = []
    unassigned_count = 0

    for shift in shifts:
        sid = shift["id"]
        assigned_ids = shift_assignments.get(sid, [])
        demand = shift.get("demand", 1)
        gap = max(0, demand - len(assigned_ids))
        unassigned_count += gap
        assigned_names = [emp_by_id[eid]["name"] for eid in assigned_ids if eid in emp_by_id]
        formatted_schedule.append(
            {
                "shift_id": sid,
                "shift_name": shift.get("name", sid),
                "demand": demand,
                "assigned_employees": assigned_names,
                "coverage_gap": gap,
                "coverage_percent": round(len(assigned_ids) / demand * 100, 2) if demand > 0 else 100.0,
            }
        )

    unassigned_employees = [e["name"] for e in employees if not employee_assigned.get(e["id"], False)]
    total_demand = sum(s.get("demand", 1) for s in shifts)
    satisfied = total_demand - unassigned_count
    confidence = satisfied / total_demand if total_demand > 0 else 1.0

    return {
        "schedule": formatted_schedule,
        "unassigned_employees": unassigned_employees,
        "labor_cost": total_labor_cost,
        "confidence_score": round(confidence, 2),
        "unassigned_shifts_count": unassigned_count,
        "solver_used": solver_used,
    }


def _empty_result(shifts: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "schedule": [
            {
                "shift_id": s.get("id", ""),
                "shift_name": s.get("name", ""),
                "demand": s.get("demand", 0),
                "assigned_employees": [],
                "coverage_gap": s.get("demand", 0),
                "coverage_percent": 0.0,
            }
            for s in shifts
        ],
        "unassigned_employees": [],
        "labor_cost": 0.0,
        "confidence_score": 0.0,
        "unassigned_shifts_count": sum(s.get("demand", 0) for s in shifts),
        "solver_used": "None (empty cluster)",
    }
