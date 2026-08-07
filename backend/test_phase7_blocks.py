"""
test_phase7_blocks.py — Test 20,000 Staff Optimization with Block-Wise Grouping, Gender Parameters, Address Proximity, and Health Conditions.
"""
import pytest
from app.services.modeling import parse_and_model_staffing
from app.services.quantum import execute_optimization_tiered

def test_20000_employees_block_wise_optimization():
    print("\n[Phase 7 Test] Generating 20,000 employee synthetic dataset...")
    
    num_employees = 20_000
    num_shifts = 5

    shifts = [
        {"id": "shift_1", "name": "Morning Shift (08:00 - 16:00)", "demand": 3000, "zone": "North Zone"},
        {"id": "shift_2", "name": "Afternoon Shift (16:00 - 00:00)", "demand": 3000, "zone": "South Zone"},
        {"id": "shift_3", "name": "Night Shift (00:00 - 08:00)", "demand": 2000, "zone": "East Zone"},
        {"id": "shift_4", "name": "Swing Shift (10:00 - 18:00)", "demand": 2000, "zone": "West Zone"},
        {"id": "shift_5", "name": "Overlapping Shift (12:00 - 20:00)", "demand": 2000, "zone": "Central Hub"}
    ]

    employees = []
    zones = ["North Zone", "South Zone", "East Zone", "West Zone", "Central Hub"]
    health_types = ["Fit", "Fit", "Fit", "Mild", "Sensitive", "Night Ineligible"]

    for i in range(num_employees):
        gender = "Male" if i < 10000 else "Female"
        address = zones[i % len(zones)]
        health = health_types[i % len(health_types)]
        
        # Availability
        avail = ["shift_1", "shift_2", "shift_3", "shift_4", "shift_5"]
        
        employees.append({
            "name": f"Employee {i+1}",
            "hourly_rate": 25.0 + (i % 5) * 5,
            "skills": ["customer_support"],
            "availability": avail,
            "gender": gender,
            "address": address,
            "health_condition": health,
        })

    data = {
        "employees": employees,
        "shifts": shifts,
        "target_males": 10000,
        "target_females": 10000,
        "block_size": 200
    }

    print("[Phase 7 Test] Modeling staffing problem...")
    model = parse_and_model_staffing(data)

    assert model["service_type"] == "staffing"
    assert len(model["employees"]) == 20000
    assert model["target_males"] == 10000
    assert model["target_females"] == 10000

    print("[Phase 7 Test] Executing Tiered Optimization Solver...")
    results = execute_optimization_tiered(model, top_n_quantum=5)

    assert "blocks" in results
    assert "block_size_100" in results["blocks"]
    assert "block_size_200" in results["blocks"]
    assert "block_size_500" in results["blocks"]

    blocks_200 = results["blocks"]["block_size_200"]
    assert len(blocks_200) == 100  # 20,000 / 200 = 100 blocks!

    # Verify Block 1 structure
    blk1 = blocks_200[0]
    assert blk1["block_id"] == "Block-1"
    assert blk1["total_staff"] == 200
    assert "gender_breakdown" in blk1
    assert "health_breakdown" in blk1
    assert len(blk1["assigned_staff"]) > 0

    print(f"[Phase 7 Test] PASSED SUCCESS! Generated {len(blocks_200)} Blocks of 200 staff each.")
    print(f"[Phase 7 Test] Block 1 Summary: {blk1['gender_breakdown']} | Health: {blk1['health_breakdown']}")

if __name__ == "__main__":
    test_20000_employees_block_wise_optimization()
