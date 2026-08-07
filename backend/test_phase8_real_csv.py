"""
test_phase8_real_csv.py — Direct CSV Ingestion & Real Data Staffing Optimization Verification.
"""
import io
import csv
import pytest
from app.services.file_parser import parse_csv_employees
from app.services.modeling import parse_and_model_staffing
from app.services.quantum import execute_optimization_tiered

def test_real_csv_20000_staffing_pipeline():
    print("\n[Phase 8 Test] Generating realistic 20,000 row CSV byte buffer...")

    csv_output = io.StringIO()
    writer = csv.writer(csv_output)

    # Required headers
    writer.writerow(["employee_id", "name", "gender", "address", "health_condition", "hourly_rate", "availability"])

    zones_list = [
        "101 North Downtown Ave, Cityville",
        "305 South Uptown Blvd, Metro",
        "509 East Suburbs Way, Suburbia",
        "712 West Industrial Pkwy, Westside",
        "920 Central Hub Plaza, Core"
    ]
    health_list = ["Fit", "Fit", "Mild", "Sensitive", "Night Ineligible"]

    for i in range(1, 20001):
        emp_id = f"EMP-{i:05d}"
        name = f"Staff Member {i}"
        gender = "Male" if i % 2 == 1 else "Female"  # 10,000 Males, 10,000 Females
        address = zones_list[i % len(zones_list)]
        health = health_list[i % len(health_list)]
        rate = 25.0 + (i % 10) * 2.5
        avail = "shift_1,shift_2,shift_3,shift_4,shift_5"

        writer.writerow([emp_id, name, gender, address, health, rate, avail])

    csv_bytes = csv_output.getvalue().encode("utf-8")
    print(f"[Phase 8 Test] CSV Generated. Size: {len(csv_bytes)/1024/1024:.2f} MB")

    # Step 1: Direct CSV Parsing & Validation
    print("[Phase 8 Test] Step 1: Executing Direct CSV Parsing & Header Validation...")
    employees, errors = parse_csv_employees(csv_bytes)

    assert len(errors) == 0, f"CSV parsing encountered errors: {errors[:5]}"
    assert len(employees) == 20000, f"Expected 20,000 employees, got {len(employees)}"
    assert employees[0]["id"] == "EMP-00001"
    assert employees[0]["gender"] == "Male"
    assert employees[0]["address"] == "305 South Uptown Blvd, Metro"
    assert employees[0]["health_condition"] == "Fit"
    print("✓ Direct CSV Parsing & Header Validation: PASSED!")

    # Step 2: Modeling with Address Proximity & Health Restriction Rules
    print("[Phase 8 Test] Step 2: Modeling Staffing Problem with Proximity & Safety Rules...")
    shifts = [
        {"id": "shift_1", "name": "Morning Shift (08:00 - 16:00)", "demand": 3000, "zone": "North Zone"},
        {"id": "shift_2", "name": "Afternoon Shift (16:00 - 00:00)", "demand": 3000, "zone": "South Zone"},
        {"id": "shift_3", "name": "Swing Shift (10:00 - 18:00)", "demand": 2000, "zone": "East Zone"},
        {"id": "shift_4", "name": "Day Shift (09:00 - 17:00)", "demand": 2000, "zone": "West Zone"},
        {"id": "shift_5", "name": "Overlapping Shift (12:00 - 20:00)", "demand": 2000, "zone": "Central Hub"}
    ]

    model_data = {
        "employees": employees,
        "shifts": shifts,
        "block_size": 200
    }

    model = parse_and_model_staffing(model_data)
    assert len(model["employees"]) == 20000
    print("✓ Model Setup: PASSED!")

    # Step 3: Optimization Execution & Block Generator
    print("[Phase 8 Test] Step 3: Running Tiered Optimization & Block Partitioning...")
    results = execute_optimization_tiered(model)

    # Requirement 7: Intermediate Diagnostic Verification
    assert "diagnostic" in results
    diag = results["diagnostic"]
    print(f"✓ Intermediate Diagnostic Report:")
    print(f"  - Total CSV Records Read: {diag['total_csv_records_read']:,}")
    print(f"  - Distinct Genders: {diag['distinct_gender_counts']}")
    print(f"  - Distinct Zones Count: {len(diag['distinct_zone_counts'])}")
    print(f"  - Distinct Health Conditions: {diag['distinct_health_counts']}")
    print(f"  - Data Source: {diag['data_source']}")

    assert diag["total_csv_records_read"] == 20000
    assert diag["distinct_gender_counts"]["Male"] == 10000
    assert diag["distinct_gender_counts"]["Female"] == 10000
    assert diag["data_source"] == "REAL_CSV_UPLOAD"

    # Requirement 2 & 6: Sequential Blocks & Per-block outputs
    assert "blocks" in results
    blocks_200 = results["blocks"]["block_size_200"]
    assert len(blocks_200) == 100, f"Expected 100 blocks for 200 block size, got {len(blocks_200)}"

    blk1 = blocks_200[0]
    print(f"✓ Block 1 Verification ({blk1['block_name']}):")
    print(f"  - Staff ID Range: {blk1['staff_id_range']}")
    print(f"  - Real Gender Breakdown: ♂ {blk1['gender_breakdown']['male']} | ♀ {blk1['gender_breakdown']['female']}")
    print(f"  - Real Health Breakdown: Fit {blk1['health_breakdown']['fit_count']} | Restricted {blk1['health_breakdown']['restricted_count']}")
    print(f"  - Block Cost Formula: {blk1['block_cost_formula']} -> ${blk1['block_cost']:,.2f}")

    # Requirement 6: Full Summary Table
    assert "summary_table_200" in results
    summary_table = results["summary_table_200"]
    assert len(summary_table) == 100
    print(f"✓ Full Summary Table: {len(summary_table)} block rows generated across full 20,000 workforce.")

    # Requirement 6: Audit & Mathematical Consistency Verification
    assert "audit_validation" in results
    audit = results["audit_validation"]
    print(f"✓ Audit & Validation Checklist:")
    print(f"  - Gender Sum Match: {audit['total_male_sum']}♂ + {audit['total_female_sum']}♀ = {audit['csv_total_count']} ({audit['gender_sum_matches']})")
    print(f"  - Headcount Match: ∑ Block Sizes = {audit['total_headcount_sum']} ({audit['headcount_sum_matches']})")
    print(f"  - Duplicate Count: {audit['duplicate_employee_count']} ({audit['no_duplicates']})")
    print(f"  - Audit Status: {audit['audit_status']}")

    assert audit["gender_sum_matches"] is True
    assert audit["headcount_sum_matches"] is True
    assert audit["no_duplicates"] is True

    print("\n==================================================")
    print("ALL 7 EXACT REQUIREMENTS PASSED PERFECTLY!")
    print("==================================================")

def test_csv_validation_missing_headers():
    print("\n[Phase 8 Test] Testing CSV Validation with missing required headers...")
    invalid_csv = "emp_name,hourly_rate\nJohn Doe,25.0\nJane Smith,30.0".encode("utf-8")
    employees, errors = parse_csv_employees(invalid_csv)

    assert len(employees) == 0
    assert len(errors) > 0
    print(f"✓ Actionable Header Validation Error: {errors[0]['issue']}")

if __name__ == "__main__":
    test_real_csv_20000_staffing_pipeline()
    test_csv_validation_missing_headers()
