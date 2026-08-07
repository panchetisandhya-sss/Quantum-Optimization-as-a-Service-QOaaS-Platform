"""
services/cluster.py — Phase 2: Pre-clustering and complexity scoring for large workforce.

Segments employees + shifts into manageable sub-problems so the solver never
needs to reason about all 30,000 employees at once.

Tunable constants are defined at module level and documented — no magic numbers buried
inside functions.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Tunable configuration constants
# ---------------------------------------------------------------------------

# Maximum number of employees in a single cluster that can be routed to the
# QAOA quantum solver.  Keep this at or below the QUBO variable budget:
# variables = employees_per_cluster × shifts_per_cluster ≤ ~32 for direct QAOA.
MAX_CLUSTER_SIZE: int = 50

# A cluster whose complexity score is >= this threshold is considered
# "high-complexity" and is a candidate for quantum routing.
HIGH_COMPLEXITY_THRESHOLD: float = 0.60

# Demand scarcity weight in the complexity score (0.0–1.0 tuning knob).
# Higher values make demand/staff ratio dominate the score.
SCARCITY_WEIGHT: float = 0.50

# Constraint overlap weight (how many shifts an employee is available for).
OVERLAP_WEIGHT: float = 0.30

# Business-priority demand threshold: shifts with demand > this value are
# flagged as "critical" and boost the cluster's score.
CRITICAL_DEMAND_THRESHOLD: int = 5

# Weight added to score when any shift in the cluster is flagged critical.
CRITICAL_DEMAND_WEIGHT: float = 0.20


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cluster_employees(
    employees: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]],
    max_cluster_size: int = MAX_CLUSTER_SIZE,
) -> List[Dict[str, Any]]:
    """
    Partition the full employee list into logical clusters based on
    availability overlap (employees available for the same shifts cluster together).

    Returns a list of cluster dicts:
      {
        "employees": List[employee_dict],
        "shifts": List[shift_dict],   # only shifts relevant to this cluster
        "cluster_id": int,
      }

    Algorithm:
      1. Build a shift → employee index.
      2. Use a greedy union-find to group employees that share any available shift.
      3. Split any group larger than max_cluster_size into equal-sized sub-groups.
    """
    if not employees or not shifts:
        return []

    shift_ids = {s["id"] for s in shifts}
    shift_by_id = {s["id"]: s for s in shifts}

    # Union-Find on employee indices
    parent = list(range(len(employees)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Group employees that share at least one available shift
    shift_to_emp_indices: Dict[str, List[int]] = {}
    for idx, emp in enumerate(employees):
        for sid in emp.get("availability", []):
            if sid in shift_ids:
                shift_to_emp_indices.setdefault(sid, []).append(idx)

    for indices in shift_to_emp_indices.values():
        for i in range(1, len(indices)):
            union(indices[0], indices[i])

    # Group by root
    groups: Dict[int, List[int]] = {}
    for idx in range(len(employees)):
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    # Build clusters, splitting oversized groups
    clusters: List[Dict[str, Any]] = []
    cluster_id = 0

    for emp_indices in groups.values():
        # Split into chunks of max_cluster_size
        chunks = [
            emp_indices[i : i + max_cluster_size]
            for i in range(0, len(emp_indices), max_cluster_size)
        ]
        for chunk in chunks:
            cluster_emps = [employees[i] for i in chunk]
            # Determine which shifts are relevant to this cluster
            cluster_shift_ids = set()
            for e in cluster_emps:
                for sid in e.get("availability", []):
                    if sid in shift_ids:
                        cluster_shift_ids.add(sid)
            cluster_shifts = [shift_by_id[sid] for sid in cluster_shift_ids]
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "employees": cluster_emps,
                    "shifts": cluster_shifts,
                }
            )
            cluster_id += 1

    return clusters


def score_cluster(cluster: Dict[str, Any]) -> float:
    """
    Compute a complexity/criticality score in [0.0, 1.0] for a cluster.

    Factors (all weights are tunable constants at module level):
      - Scarcity ratio: demand / available_employees (capped at 1.0)
      - Constraint overlap: avg. number of shifts each employee is available for
        (more choices = more complex assignment problem)
      - Critical demand flag: any shift with demand > CRITICAL_DEMAND_THRESHOLD

    Returns a float in [0.0, 1.0] where 1.0 = maximally complex/critical.
    """
    employees = cluster.get("employees", [])
    shifts = cluster.get("shifts", [])

    if not employees or not shifts:
        return 0.0

    # --- Scarcity component ---
    total_demand = sum(s.get("demand", 1) for s in shifts)
    available_count = len(employees)
    # Ratio > 1 means demand exceeds staff (scarce), capped at 1.0
    scarcity_ratio = min(1.0, total_demand / max(available_count, 1))

    # --- Constraint overlap component ---
    shift_id_set = {s["id"] for s in shifts}
    avg_availability = sum(
        len([sid for sid in e.get("availability", []) if sid in shift_id_set])
        for e in employees
    ) / max(len(employees), 1)
    # Normalise: more shifts available per employee = higher overlap complexity
    num_shifts = max(len(shifts), 1)
    overlap_ratio = min(1.0, avg_availability / num_shifts)

    # --- Critical demand flag ---
    has_critical = any(
        s.get("demand", 0) > CRITICAL_DEMAND_THRESHOLD for s in shifts
    )
    critical_bonus = CRITICAL_DEMAND_WEIGHT if has_critical else 0.0

    score = (
        SCARCITY_WEIGHT * scarcity_ratio
        + OVERLAP_WEIGHT * overlap_ratio
        + critical_bonus
    )
    return min(1.0, score)
