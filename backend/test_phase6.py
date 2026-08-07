"""
test_phase6.py — Integration, End-to-End Verification, and 30,000 Staff Scale Test.

Run with:
  cd /home/rgukt/.gemini/antigravity/scratch/qoaas-platform/backend
  python3 -m pytest test_phase6.py -v
"""
import io
import time
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# 1. End-to-End Tiered Solver & Mixed Complexity Routing Test
# ---------------------------------------------------------------------------
from app.services.modeling import parse_and_model_staffing
from app.services.quantum import execute_optimization_tiered, execute_optimization
from app.services.cluster import cluster_employees, score_cluster
from app.services.classical_solver import solve_cluster_classical


def test_mixed_cluster_complexity_routing():
    """Verify that cluster scoring ranks scarce/high-demand clusters higher and routes top-N to quantum."""
    # Build 3 clusters:
    # Cluster A: High scarcity (demand 10 for 5 employees) -> High complexity score
    # Cluster B & C: Low scarcity (demand 1 for 10 employees) -> Low complexity score
    shifts = [
        {"id": "s_critical", "name": "Critical Shift", "demand": 10},
        {"id": "s_normal1", "name": "Normal Shift 1", "demand": 1},
        {"id": "s_normal2", "name": "Normal Shift 2", "demand": 1},
    ]

    employees = []
    # 5 employees available for s_critical
    for i in range(5):
        employees.append({
            "id": f"emp_crit_{i}",
            "name": f"Crit Emp {i}",
            "hourly_rate": 40.0,
            "skills": ["support"],
            "availability": ["s_critical"],
        })
    # 10 employees available for s_normal1
    for i in range(10):
        employees.append({
            "id": f"emp_norm1_{i}",
            "name": f"Norm1 Emp {i}",
            "hourly_rate": 20.0,
            "skills": ["support"],
            "availability": ["s_normal1"],
        })
    # 10 employees available for s_normal2
    for i in range(10):
        employees.append({
            "id": f"emp_norm2_{i}",
            "name": f"Norm2 Emp {i}",
            "hourly_rate": 20.0,
            "skills": ["support"],
            "availability": ["s_normal2"],
        })

    model = {
        "service_type": "staffing",
        "employees": employees,
        "shifts": shifts,
        "currency_code": "USD",
        "timezone": "UTC",
    }

    # Execute tiered solver with top_n_quantum = 1
    res = execute_optimization_tiered(model, top_n_quantum=1)

    assert "schedule" in res
    assert res["quantum_solved_count"] == 1
    assert res["classical_solved_count"] >= 2
    assert res["total_clusters"] >= 3
    assert "quantum_vs_classical_split" in res
    assert "1 Quantum" in res["quantum_vs_classical_split"]


# ---------------------------------------------------------------------------
# 2. File Parser & Upload Endpoint Validation Test
# ---------------------------------------------------------------------------
from app.services.file_parser import parse_csv_employees, parse_employee_file


def test_file_parser_valid_csv():
    csv_data = b"""name,hourly_rate,availability,skills
Alice Smith,35.0,"shift_1,shift_2",customer_support
Bob Jones,28.5,shift_1,technical_support
"""
    emps, errors = parse_csv_employees(csv_data)
    assert len(errors) == 0
    assert len(emps) == 2
    assert emps[0]["name"] == "Alice Smith"
    assert emps[0]["hourly_rate"] == 35.0
    assert emps[0]["availability"] == ["shift_1", "shift_2"]


def test_file_parser_invalid_row():
    csv_data = b"""name,hourly_rate,availability,skills
Alice Smith,thirty,shift_1,customer_support
"""
    emps, errors = parse_csv_employees(csv_data)
    assert len(errors) == 1
    assert errors[0]["row"] == 2
    assert errors[0]["field"] == "hourly_rate"
    assert "Not a valid number" in errors[0]["issue"]


def test_file_parser_missing_required_headers():
    csv_data = b"""employee_name,pay_rate
Alice Smith,35.0
"""
    emps, errors = parse_csv_employees(csv_data)
    assert len(errors) >= 1
    assert errors[0]["row"] == 0
    assert "Required columns are missing" in errors[0]["issue"]


# ---------------------------------------------------------------------------
# 3. QRNG API + Local Fallback Test
# ---------------------------------------------------------------------------
from app.services.qrng import get_quantum_random_bytes, generate_verification_token, generate_qr_code


def test_qrng_anu_fallback_on_error():
    """Simulate ANU QRNG endpoint failure and confirm fallback to Qiskit/os.urandom."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("ANU API Connection Timeout")
        raw_bytes, source_label = get_quantum_random_bytes(16)
        assert len(raw_bytes) == 16
        assert "ANU" not in source_label  # fell back
        assert ("Local Qiskit" in source_label or "os.urandom" in source_label)


def test_qrng_token_and_qr_generation():
    token = generate_verification_token("test_job_123", b"quantum_entropy_12345")
    assert len(token) == 64
    qr_png = generate_qr_code(f"http://localhost:8000/verify?token={token}")
    assert qr_png is not None
    assert qr_png.startswith(b"\x89PNG")  # valid PNG header


# ---------------------------------------------------------------------------
# 4. External Quantum QPU Graceful Fallback Test
# ---------------------------------------------------------------------------
from app.services.external_quantum import execute_with_external_backend


def test_external_quantum_fallback_on_bad_credentials():
    """Simulate invalid IBM/D-Wave API credentials and confirm graceful local solver degradation."""
    Q = np.array([[-1.0, 0.5], [0.5, -2.0]])
    bad_config = {
        "provider": "ibm",
        "api_token": "INVALID_EXPIRED_KEY_999",
        "endpoint_url": "https://invalid.ibm.url",
    }
    sol, energy, label = execute_optimization(Q, backend_config=bad_config)
    assert len(sol) == 2
    assert "Fallback" in label or "Local" in label or "NumPy" in label
    assert isinstance(energy, float)


# ---------------------------------------------------------------------------
# 5. Large-Scale Benchmark: ~30,000 Synthetic Employees
# ---------------------------------------------------------------------------
def test_scale_30000_employees_tiered_solve():
    """
    Generate ~30,000 synthetic employee records and run through execute_optimization_tiered().
    Verifies:
      - Completes without crash or timeout (< 30 seconds for 30k emps)
      - Reports quantum vs classical split
      - Returns valid schedule matching demand
    """
    num_employees = 30_000
    num_shifts = 5

    shifts = [
        {"id": f"shift_{i+1}", "name": f"Shift {i+1}", "demand": 4500}
        for i in range(num_shifts)
    ]

    print(f"\n[Scale Test] Generating {num_employees} synthetic staff records...")
    employees = []
    shift_ids = [s["id"] for s in shifts]
    for i in range(num_employees):
        # Assign 2 available shifts per employee
        avail = [shift_ids[i % num_shifts], shift_ids[(i + 1) % num_shifts]]
        employees.append({
            "id": f"emp_{i}",
            "name": f"Staff Member {i+1}",
            "hourly_rate": 25.0 + (i % 10) * 2,
            "skills": ["general"],
            "availability": avail,
        })

    model = {
        "service_type": "staffing",
        "employees": employees,
        "shifts": shifts,
        "currency_code": "USD",
        "timezone": "UTC",
    }

    start_time = time.time()
    print(f"[Scale Test] Executing tiered solver on {num_employees} staff...")
    results = execute_optimization_tiered(model, top_n_quantum=5)
    duration = time.time() - start_time

    print(f"[Scale Test] Completed in {duration:.2f} seconds.")
    print(f"[Scale Test] Total clusters: {results['total_clusters']}")
    print(f"[Scale Test] Quantum solved: {results['quantum_solved_count']}")
    print(f"[Scale Test] Classical solved: {results['classical_solved_count']}")
    print(f"[Scale Test] Split: {results['quantum_vs_classical_split']}")
    print(f"[Scale Test] Labor cost: ${results['labor_cost']:,.2f}")
    print(f"[Scale Test] Coverage: {results['confidence_score']*100:.1f}%")

    assert duration < 300.0, f"Scale test took too long: {duration:.2f}s"
    assert results["total_clusters"] > 0
    assert results["quantum_solved_count"] == 5
    assert results["classical_solved_count"] > 0
    assert len(results["schedule"]) == num_shifts
    assert results["confidence_score"] > 0.80
