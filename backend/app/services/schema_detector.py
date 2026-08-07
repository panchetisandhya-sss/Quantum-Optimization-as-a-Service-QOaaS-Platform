"""
services/schema_detector.py — Generic Schema Detection & Semantic Column Mapping Engine

Inspects any uploaded finance CSV / data structure to determine the underlying
business meaning and mathematical problem type:
  1. PORTFOLIO_PRICES   (Historical asset price time series -> calculate period returns -> Markowitz)
  2. PORTFOLIO_RETURNS  (Pre-calculated asset return percentage observations -> Markowitz)
  3. BUDGET_ALLOCATION  (Organizational finance, department expenses, headcount, savings -> 0-1 Knapsack QUBO)

Guarantees:
  - Never forces an organizational finance CSV into a portfolio optimizer.
  - Never treats absolute currency balances (Revenue, Budget, Expense) as return rates (R_i).
  - Handles flexible column casing, spaces, underscores, currency suffixes (_INR, _USD), and common synonyms.
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Semantic Column Synonyms & Match Patterns
# ---------------------------------------------------------------------------

SYNONYMS: Dict[str, List[str]] = {
    "identifier": [
        "record_id", "record", "id", "organization", "org", "department", "dept",
        "asset", "symbol", "ticker", "security", "name", "company", "code", "entity"
    ],
    "date": [
        "date", "timestamp", "time", "period", "day", "month", "year", "dt"
    ],
    "revenue": [
        "revenue", "revenue_inr", "revenue_usd", "annual_revenue", "total_revenue", "sales", "turnover"
    ],
    "budget": [
        "budget", "budget_inr", "budget_usd", "allocated_budget", "max_budget", "cost_limit", "spending_cap"
    ],
    "expense": [
        "actual_expense", "expense", "expense_inr", "expense_usd", "actual_expense_inr", "cost", "current_cost", "spending"
    ],
    "savings": [
        "potential_savings", "potential_savings_inr", "potential_savings_usd", "savings", "cost_reduction", "cost_savings"
    ],
    "headcount": [
        "headcount", "employees", "employee_count", "staff", "capacity", "resources", "workers"
    ],
    "margin": [
        "current_margin", "current_margin_inr", "margin", "profit_margin", "operating_margin", "optimized_margin_inr"
    ],
    "optimization_target": [
        "optimization_target_%", "optimization_target", "target_%", "savings_target_%", "reduction_target"
    ],
    "price": [
        "price", "close", "adj_close", "adjusted_close", "unit_price", "nav", "stock_price"
    ],
    "return": [
        "return", "daily_return", "monthly_return", "expected_return", "yield", "pct_change", "annual_return"
    ],
    "risk": [
        "risk", "volatility", "variance", "std_dev", "standard_deviation"
    ]
}


def _normalize_col(name: str) -> str:
    """Clean column name: lowercase, strip whitespace and quotes, replace spaces with underscores."""
    if not isinstance(name, str):
        return ""
    clean = name.strip().lower().replace("'", "").replace('"', "")
    clean = re.sub(r"\s+", "_", clean)
    return clean


def detect_column_semantics(headers: List[str]) -> Dict[str, Optional[str]]:
    """
    Maps list of raw CSV header names to canonical semantic categories.
    Returns dict: category -> matched_header_name (or None)
    """
    mapped: Dict[str, Optional[str]] = {cat: None for cat in SYNONYMS}
    used_headers = set()

    normalized_headers = [(_normalize_col(h), h) for h in headers]

    # Exact or substring synonym matching
    for cat, patterns in SYNONYMS.items():
        for norm_h, raw_h in normalized_headers:
            if raw_h in used_headers:
                continue

            # Exact match first
            if norm_h in patterns:
                mapped[cat] = raw_h
                used_headers.add(raw_h)
                break

        # Substring search if exact match not found
        if mapped[cat] is None:
            for cat_pat in patterns:
                for norm_h, raw_h in normalized_headers:
                    if raw_h in used_headers:
                        continue
                    if cat_pat in norm_h or norm_h in cat_pat:
                        mapped[cat] = raw_h
                        used_headers.add(raw_h)
                        break
                if mapped[cat] is not None:
                    break

    return mapped


def detect_csv_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyzes pandas DataFrame to determine problem type and field mappings.
    
    Problem Types:
      - "budget_allocation": Contains Budget/Expense/Savings/Headcount/Organization fields.
      - "portfolio_prices": Contains Date/Asset/Price time series data.
      - "portfolio_returns": Contains Asset/Return/Risk data.
    """
    headers = [str(c) for c in df.columns]
    mapping = detect_column_semantics(headers)

    has_budget = mapping["budget"] is not None
    has_savings = mapping["savings"] is not None
    has_expense = mapping["expense"] is not None
    has_revenue = mapping["revenue"] is not None
    has_headcount = mapping["headcount"] is not None
    has_price = mapping["price"] is not None
    has_return = mapping["return"] is not None
    has_date = mapping["date"] is not None
    has_asset = mapping["identifier"] is not None

    # Classification Logic
    if (has_budget or has_savings or has_expense or has_revenue or has_headcount) and not (has_price or has_return):
        problem_type = "budget_allocation"
    elif has_price or (has_date and not has_return):
        problem_type = "portfolio_prices"
    elif has_return:
        problem_type = "portfolio_returns"
    elif len(df.columns) >= 2:
        # Fallback: check if values are large currency balances vs percentages
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            max_val = df[numeric_cols].abs().max().max()
            if max_val > 5.0:  # Values > 500% -> Organizational balances, not returns!
                problem_type = "budget_allocation"
            else:
                problem_type = "portfolio_returns"
        else:
            problem_type = "budget_allocation"
    else:
        problem_type = "budget_allocation"

    return {
        "problem_type": problem_type,
        "mapping": mapping,
        "raw_headers": headers,
        "num_rows": len(df),
        "num_cols": len(df.columns)
    }


def parse_and_validate_finance_csv(
    file_bytes: bytes,
    filename: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Reads file bytes, detects schema, and constructs validated dataset structure.
    Returns:
      (processed_payload, errors, schema_info)
    """
    errors: List[Dict[str, Any]] = []

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("latin-1")
        except Exception as exc:
            return {}, [{"row": 0, "field": "file", "issue": f"Cannot decode file: {exc}"}], {}

    import io
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as exc:
        return {}, [{"row": 0, "field": "file", "issue": f"Malformed CSV file: {exc}"}], {}

    if df.empty:
        return {}, [{"row": 0, "field": "file", "issue": "Uploaded CSV file is empty."}], {}

    schema_info = detect_csv_schema(df)
    problem_type = schema_info["problem_type"]
    mapping = schema_info["mapping"]

    processed_payload: Dict[str, Any] = {
        "problem_type": problem_type,
        "filename": filename,
        "num_records": len(df)
    }

    if problem_type == "budget_allocation":
        # Process organizational budget data
        id_col = mapping["identifier"] or df.columns[0]
        budget_col = mapping["budget"]
        savings_col = mapping["savings"]
        expense_col = mapping["expense"]
        revenue_col = mapping["revenue"]
        headcount_col = mapping["headcount"]
        target_col = mapping["optimization_target"]

        records = []
        for idx, row in df.iterrows():
            rec_id = str(row[id_col]) if id_col in row and pd.notna(row[id_col]) else f"ORG-{idx+1:03d}"
            
            # Numeric fields with safe parsing
            revenue = float(row[revenue_col]) if revenue_col and pd.notna(row.get(revenue_col)) else 0.0
            budget = float(row[budget_col]) if budget_col and pd.notna(row.get(budget_col)) else 100000.0
            expense = float(row[expense_col]) if expense_col and pd.notna(row.get(expense_col)) else budget * 0.9
            headcount = int(row[headcount_col]) if headcount_col and pd.notna(row.get(headcount_col)) else 10
            
            # Savings objective calculation
            if savings_col and pd.notna(row.get(savings_col)):
                potential_savings = float(row[savings_col])
            elif target_col and pd.notna(row.get(target_col)):
                target_pct = float(str(row[target_col]).replace("%", ""))
                if target_pct > 1.0:
                    target_pct /= 100.0
                potential_savings = expense * target_pct
            else:
                potential_savings = expense * 0.15  # Default 15% estimated savings potential

            records.append({
                "record_id": rec_id,
                "revenue": max(0.0, revenue),
                "budget": max(1.0, budget),
                "actual_expense": max(0.0, expense),
                "potential_savings": max(0.0, potential_savings),
                "headcount": max(1, headcount)
            })

        processed_payload["records"] = records
        processed_payload["detected_fields"] = {
            "identifier_col": id_col,
            "budget_col": budget_col or "Defaulted",
            "savings_col": savings_col or target_col or "Derived (15%)",
            "expense_col": expense_col or "Derived",
            "headcount_col": headcount_col or "Defaulted"
        }

    else:
        # Process Portfolio Investment data
        id_col = mapping["identifier"] or df.columns[0]

        if problem_type == "portfolio_prices" and mapping["date"] and id_col in df.columns:
            # Pivot historical prices to compute period returns: returns = prices.pct_change()
            try:
                date_col = mapping["date"]
                price_col = mapping["price"] or df.columns[-1]
                pivot_df = df.pivot(index=date_col, columns=id_col, values=price_col)
                returns_df = pivot_df.pct_change().dropna()

                assets = []
                for col in returns_df.columns:
                    ret_series = returns_df[col]
                    exp_ret = float(ret_series.mean() * 252)  # Annualized
                    vol = float(ret_series.std() * np.sqrt(252))
                    assets.append({
                        "asset": str(col),
                        "return": round(exp_ret, 4),
                        "risk": round(max(0.01, vol), 4)
                    })
                processed_payload["assets"] = assets
            except Exception:
                # Fallback row-by-row parsing
                problem_type = "portfolio_returns"

        if problem_type == "portfolio_returns" or "assets" not in processed_payload:
            ret_col = mapping["return"] or df.columns[1] if len(df.columns) > 1 else None
            risk_col = mapping["risk"]

            assets = []
            for idx, row in df.iterrows():
                asset_name = str(row[id_col]) if id_col in row and pd.notna(row[id_col]) else f"Asset_{idx+1}"
                
                raw_ret = float(row[ret_col]) if ret_col and pd.notna(row.get(ret_col)) else 0.08
                # Guardrail: Handle percentage vs decimal scale (e.g. 14 -> 0.14)
                if abs(raw_ret) > 2.0:
                    raw_ret = raw_ret / 100.0

                raw_risk = float(row[risk_col]) if risk_col and pd.notna(row.get(risk_col)) else 0.10
                if raw_risk > 2.0:
                    raw_risk = raw_risk / 100.0

                assets.append({
                    "asset": asset_name,
                    "return": round(raw_ret, 4),
                    "risk": round(max(0.01, raw_risk), 4)
                })

            processed_payload["assets"] = assets

    return processed_payload, errors, schema_info
