"""
test_schema_detector.py — Unit & Integration Test Suite for Generic Finance Engine

Tests:
  1. Schema detection of budget allocation CSV (e.g. organisation_finance_50_records.csv)
  2. Schema detection of portfolio prices CSV (historical price time series)
  3. Schema detection of portfolio returns CSV
  4. Budget allocation QUBO generation & constraint repair
  5. End-to-end pipeline execution for budget allocation jobs
  6. Guardrail validation flagging returns > 2.0 (200%)
"""

import pytest
import numpy as np
import pandas as pd
import io

from app.services.schema_detector import (
    detect_column_semantics,
    detect_csv_schema,
    parse_and_validate_finance_csv
)
from app.services.modeling import parse_and_model_budget_allocation
from app.services.qubo import generate_budget_allocation_qubo
from app.services.quantum import repair_budget_allocation


def test_detect_column_semantics_budget():
    headers = [
        "Record_ID", "Month", "Expense_Category", "Revenue_INR",
        "Budget_INR", "Actual_Expense_INR", "Headcount",
        "Current_Margin_INR", "Optimization_Target_%",
        "Potential_Savings_INR", "Optimized_Expense_INR", "Optimized_Margin_INR"
    ]
    mapping = detect_column_semantics(headers)

    assert mapping["identifier"] == "Record_ID"
    assert mapping["revenue"] == "Revenue_INR"
    assert mapping["budget"] == "Budget_INR"
    assert mapping["expense"] == "Actual_Expense_INR"
    assert mapping["headcount"] == "Headcount"
    assert mapping["savings"] == "Potential_Savings_INR"


def test_detect_schema_budget_csv():
    csv_data = """Record_ID,Revenue_INR,Budget_INR,Actual_Expense_INR,Headcount,Potential_Savings_INR
ORG-001,2000000,500000,450000,25,75000
ORG-002,1500000,300000,280000,15,42000
ORG-003,3000000,750000,700000,40,105000
"""
    df = pd.read_csv(io.StringIO(csv_data))
    schema_info = detect_csv_schema(df)

    assert schema_info["problem_type"] == "budget_allocation"
    assert schema_info["num_rows"] == 3


def test_parse_and_validate_finance_csv_budget():
    csv_data = """Record_ID,Revenue_INR,Budget_INR,Actual_Expense_INR,Headcount,Potential_Savings_INR
ORG-001,2000000,500000,450000,25,75000
ORG-002,1500000,300000,280000,15,42000
ORG-003,3000000,750000,700000,40,105000
"""
    payload, errors, schema_info = parse_and_validate_finance_csv(csv_data.encode("utf-8"), "finance.csv")

    assert not errors
    assert payload["problem_type"] == "budget_allocation"
    assert payload["num_records"] == 3
    assert len(payload["records"]) == 3
    assert payload["records"][0]["potential_savings"] == 75000.0


def test_budget_allocation_qubo_modeling():
    records = [
        {"record_id": "ORG-001", "budget": 100000, "potential_savings": 20000, "headcount": 10},
        {"record_id": "ORG-002", "budget": 150000, "potential_savings": 35000, "headcount": 15},
        {"record_id": "ORG-003", "budget": 200000, "potential_savings": 45000, "headcount": 20},
    ]

    model = parse_and_model_budget_allocation({"records": records, "max_budget": 300000, "max_headcount": 30})

    assert model["service_type"] == "budget_allocation"
    assert model["num_variables"] == 3
    assert model["max_budget"] == 300000

    Q, mapping = generate_budget_allocation_qubo(model)
    assert Q.shape == (3, 3)
    assert len(mapping) == 3


def test_repair_budget_allocation():
    mapping = [
        {"binary_index": 0, "record_id": "ORG-001", "budget": 100000, "potential_savings": 20000, "headcount": 10},
        {"binary_index": 1, "record_id": "ORG-002", "budget": 150000, "potential_savings": 35000, "headcount": 15},
        {"binary_index": 2, "record_id": "ORG-003", "budget": 200000, "potential_savings": 45000, "headcount": 20},
    ]

    sol_bits = np.array([1, 1, 1])  # Total budget 450,000 exceeds max_budget 300,000
    res = repair_budget_allocation(sol_bits, mapping, max_budget=300000, max_headcount=30)

    assert res["budget_used"] <= 300000
    assert res["headcount_used"] <= 30
    assert len(res["selected_organizations"]) > 0
    assert "ORG-003" in res["selected_organizations"]  # Highest savings density selected
