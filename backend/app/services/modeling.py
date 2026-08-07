from typing import Dict, Any, List
import numpy as np
from app.config import settings

def parse_and_model_portfolio(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses portfolio assets data.
    Input structure should contain:
    - assets: List of dicts with keys (name/ticker, return, risk)
    - risk_aversion: float (optional, default 0.5)
    - covariance: Optional matrix (list of lists)
    """
    assets = data.get("assets", [])
    risk_aversion = float(data.get("risk_aversion", 0.5))
    currency_code = data.get("currency_code", settings.DEFAULT_CURRENCY)
    timezone = data.get("timezone", settings.DEFAULT_TIMEZONE)

    if not assets:
        raise ValueError("No assets provided for portfolio optimization.")
        
    num_assets = len(assets)
    names = []
    returns = []
    risks = []
    
    # Standardize column extraction
    for idx, asset in enumerate(assets):
        name = asset.get("asset") or asset.get("ticker") or asset.get("name") or f"Asset_{idx+1}"
        ret = float(asset.get("return") or asset.get("expected_return") or 0.0)
        risk = float(asset.get("risk") or asset.get("volatility") or 0.05)
        names.append(name)
        returns.append(ret)
        risks.append(risk)

    # Auto-detection check: If returns contain large monetary figures (> 5.0) or names look like ORG-001/Record IDs
    is_monetary_balances = any(abs(r) > 5.0 for r in returns) or any(n.startswith("ORG-") or n.startswith("Record_") for n in names)
    if is_monetary_balances:
        converted_records = []
        for idx, asset in enumerate(assets):
            rec_id = names[idx]
            val = returns[idx]
            converted_records.append({
                "record_id": rec_id,
                "revenue": val if val > 0 else 100000.0,
                "budget": val * 0.8 if val > 0 else 80000.0,
                "actual_expense": val * 0.7 if val > 0 else 70000.0,
                "potential_savings": val * 0.15 if val > 0 else 15000.0,
                "headcount": 10
            })
        return parse_and_model_budget_allocation({
            "records": converted_records,
            "currency_code": currency_code,
            "timezone": timezone
        })

        
    # Auto-generate covariance matrix if not provided
    covariance = data.get("covariance")
    if not covariance:
        cov_matrix = np.zeros((num_assets, num_assets))
        for i in range(num_assets):
            for j in range(num_assets):
                if i == j:
                    cov_matrix[i, j] = risks[i] ** 2
                else:
                    # Assume positive correlation between assets (e.g. 0.3 average)
                    correlation = 0.3
                    cov_matrix[i, j] = correlation * risks[i] * risks[j]
        covariance = cov_matrix.tolist()
    
    # Generate formal mathematical representation
    latex_formulation = {
        "variables": [f"w_{{{name}}} \\ge 0" for name in names],
        "objective": f"\\min \\left( \\sum_{{i,j}} w_i w_j \\Sigma_{{i,j}} - {risk_aversion} \\sum_i w_i R_i \\right)",
        "constraints": ["\\sum_i w_i = 1.0"]
    }
    
    # Store variables description
    variables_metadata = []
    for i, name in enumerate(names):
        variables_metadata.append({
            "id": f"w_{i}",
            "name": name,
            "type": "continuous [0, 1]",
            "expected_return": returns[i],
            "risk": risks[i]
        })

    organization_name = data.get("organization_name") or data.get("company_name") or "Quantum Dynamics Corp"

    model_representation = {
        "service_type": "portfolio",
        "organization_name": organization_name,
        "num_variables": num_assets,
        "variables": variables_metadata,
        "returns": returns,
        "covariance": covariance,
        "risk_aversion": risk_aversion,
        "latex_formulation": latex_formulation,
        "raw_names": names,
        "currency_code": currency_code,
        "timezone": timezone,
    }
    
    return model_representation

def parse_and_model_staffing(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses staffing scheduling data.
    Input structure should contain:
    - employees: List of dicts (name, hourly_rate, skills, availability)
    - shifts: List of dicts (id, start_time, end_time, demand_qty)
    """
    employees = data.get("employees", [])
    shifts = data.get("shifts", [])
    organization_name = data.get("organization_name") or data.get("company_name") or "Quantum Dynamics Corp"
    currency_code = data.get("currency_code", settings.DEFAULT_CURRENCY)
    timezone = data.get("timezone", settings.DEFAULT_TIMEZONE)

    if not employees or not shifts:
        raise ValueError("Employees and shifts are required for staffing optimization.")
        
    # Standardize employees list
    emp_list = []

    def map_address_to_zone(addr: str) -> str:
        a = str(addr).lower()
        if "north" in a or "downtown" in a or any(p in a for p in ["10", "11", "12", "20"]):
            return "North Zone"
        elif "south" in a or "uptown" in a or any(p in a for p in ["30", "31", "32", "40"]):
            return "South Zone"
        elif "east" in a or "suburbs" in a or any(p in a for p in ["50", "51", "52", "60"]):
            return "East Zone"
        elif "west" in a or "industrial" in a or any(p in a for p in ["70", "71", "72", "80"]):
            return "West Zone"
        else:
            return "Central Hub"

    for idx, emp in enumerate(employees):
        e_id = emp.get("id") or f"emp_{idx+1}"
        name = emp.get("name") or f"Employee_{idx+1}"
        rate = float(emp.get("hourly_rate") or emp.get("rate") or 25.0)
        skills = emp.get("skills") or ["general"]
        avail = emp.get("availability") or [s.get("id") for s in shifts]

        gender_raw = str(emp.get("gender") or emp.get("sex") or "Male").strip()
        gender = "Female" if gender_raw.lower().startswith("f") or gender_raw.lower().startswith("woman") else "Male"

        raw_addr = emp.get("address") or emp.get("zone") or emp.get("city") or emp.get("pincode") or "North Zone"
        zone = map_address_to_zone(raw_addr)

        health = str(emp.get("health_condition") or emp.get("health_status") or "Fit").strip()
        h_lower = health.lower()

        # Health restriction rule
        is_restricted = any(kw in h_lower for kw in ["ineligible", "sensitive", "chronic", "mobility", "pregnant"])
        if is_restricted:
            health_rule = f"Health Rule: Restricted from Night Shift ({health}) → Routed to Day/Morning Shift"
        else:
            health_rule = f"Health Rule: Full Shift Eligibility ({health})"

        emp_list.append({
            "id": e_id,
            "name": name,
            "hourly_rate": rate,
            "skills": skills,
            "availability": avail,
            "gender": gender,
            "address": raw_addr,
            "zone": zone,
            "health_condition": health,
            "is_health_restricted": is_restricted,
            "health_rule": health_rule,
        })

    # Stratified interleaving across dataset to prevent accidental gender clustering
    males = [e for e in emp_list if e["gender"] == "Male"]
    females = [e for e in emp_list if e["gender"] == "Female"]
    stratified_list = []
    m_idx, f_idx = 0, 0
    total_len = len(emp_list)

    while len(stratified_list) < total_len:
        if m_idx < len(males):
            stratified_list.append(males[m_idx])
            m_idx += 1
        if f_idx < len(females):
            stratified_list.append(females[f_idx])
            f_idx += 1

    emp_list = stratified_list

    # Standardize shifts list
    shift_list = []
    default_shift_zones = ["North Zone", "South Zone", "East Zone", "West Zone", "Central Hub"]
    for idx, s in enumerate(shifts):
        s_id = s.get("id") or f"shift_{idx+1}"
        name = s.get("name") or f"Shift {idx+1}"
        demand = int(s.get("demand") or s.get("demand_qty") or 1)
        zone = s.get("zone") or default_shift_zones[idx % len(default_shift_zones)]
        shift_list.append({
            "id": s_id,
            "name": name,
            "demand": demand,
            "zone": zone,
        })

    # Address proximity explanation per employee
    shift_by_zone = {s["zone"]: s for s in shift_list}
    for e in emp_list:
        assigned_shift_info = shift_by_zone.get(e["zone"], shift_list[0])
        e["proximity_rule"] = f"Zone Mapping: '{e['address']}' → {e['zone']} → Proximity Shift '{assigned_shift_info['name']}'"

    num_employees = len(emp_list)
    num_shifts = len(shift_list)

    # Binary decision variables x_{e, s}
    decision_variables = []
    variables_metadata = []
    for e in emp_list:
        for s in shift_list:
            var_id = f"x_{e['id']}_{s['id']}"
            is_available = s['id'] in e['availability']
            decision_variables.append(var_id)
            variables_metadata.append({
                "id": var_id,
                "employee_id": e['id'],
                "employee_name": e['name'],
                "shift_id": s['id'],
                "shift_name": s['name'],
                "is_available": is_available,
                "cost": e['hourly_rate'],
                "type": "binary"
            })
            
    # Generate formal mathematical representation
    latex_formulation = {
        "variables": ["x_{e,s} \\in \\{0,1\\} \\quad \\forall e \\in E, s \\in S"],
        "objective": "\\min \\sum_{e,s} C_e x_{e,s}",
        "constraints": [
            "\\sum_e x_{e,s} \\ge D_s \\quad \\forall s \\in S \\quad \\text{(Demand coverage)}",
            "\\sum_s x_{e,s} \\le 1 \\quad \\forall e \\in E \\quad \\text{(Max shift constraint)}",
            "x_{e,s} = 0 \\quad \\text{if health safety restricted (e.g. Night Ineligible for Night Shift)}"
        ]
    }
    
    target_males = data.get("target_males") or sum(1 for e in emp_list if e["gender"] == "Male")
    target_females = data.get("target_females") or sum(1 for e in emp_list if e["gender"] == "Female")
    block_size = int(data.get("block_size") or 200)

    model_representation = {
        "service_type": "staffing",
        "organization_name": organization_name,
        "num_variables": len(decision_variables),
        "variables": variables_metadata,
        "employees": emp_list,
        "shifts": shift_list,
        "target_males": target_males,
        "target_females": target_females,
        "block_size": block_size,
        "latex_formulation": latex_formulation,
        "currency_code": currency_code,
        "timezone": timezone,
    }
    
    return model_representation


def parse_and_model_budget_allocation(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses organizational budget allocation records.
    Input structure should contain:
    - records: List of dicts (record_id, budget, actual_expense, potential_savings, headcount, revenue)
    - max_budget: Optional float cap (default: 80% of total budget sum)
    - max_headcount: Optional int cap
    """
    records = data.get("records", [])
    currency_code = data.get("currency_code", settings.DEFAULT_CURRENCY)
    timezone = data.get("timezone", settings.DEFAULT_TIMEZONE)

    if not records:
        raise ValueError("No organizational records provided for budget allocation optimization.")

    num_records = len(records)
    total_budget_sum = sum(float(r.get("budget", 0.0)) for r in records)
    total_headcount_sum = sum(int(r.get("headcount", 0)) for r in records)

    # Configurable budget cap (default 80% of sum if not explicitly passed)
    max_budget = float(data.get("max_budget") or (total_budget_sum * 0.80 if total_budget_sum > 0 else 1000000.0))
    max_headcount = int(data.get("max_headcount") or (total_headcount_sum * 0.85 if total_headcount_sum > 0 else 500))

    variables_metadata = []
    savings_vector = []
    budget_vector = []
    headcount_vector = []
    record_ids = []

    for idx, rec in enumerate(records):
        rec_id = str(rec.get("record_id") or f"ORG-{idx+1:03d}")
        budget = float(rec.get("budget", 0.0))
        savings = float(rec.get("potential_savings", 0.0))
        headcount = int(rec.get("headcount", 1))

        record_ids.append(rec_id)
        savings_vector.append(savings)
        budget_vector.append(budget)
        headcount_vector.append(headcount)

        variables_metadata.append({
            "id": f"x_{idx}",
            "record_id": rec_id,
            "type": "binary {0,1}",
            "budget": budget,
            "potential_savings": savings,
            "headcount": headcount,
            "actual_expense": float(rec.get("actual_expense", budget * 0.9)),
            "revenue": float(rec.get("revenue", 0.0))
        })

    latex_formulation = {
        "variables": [f"x_{{{rid}}} \\in \\{{0,1\\}}" for rid in record_ids],
        "objective": "\\max \\sum_i \\text{PotentialSavings}_i x_i \\quad \\equiv \\quad \\min -\\sum_i S_i x_i",
        "constraints": [
            f"\\sum_i \\text{{Budget}}_i x_i \\le {max_budget:,.2f} \\quad \\text{{(Budget Cap)}}",
            f"\\sum_i \\text{{Headcount}}_i x_i \\le {max_headcount} \\quad \\text{{(Capacity Cap)}}"
        ]
    }

    model_representation = {
        "service_type": "budget_allocation",
        "num_variables": num_records,
        "variables": variables_metadata,
        "record_ids": record_ids,
        "savings_vector": savings_vector,
        "budget_vector": budget_vector,
        "headcount_vector": headcount_vector,
        "max_budget": max_budget,
        "max_headcount": max_headcount,
        "total_budget_sum": total_budget_sum,
        "total_headcount_sum": total_headcount_sum,
        "latex_formulation": latex_formulation,
        "currency_code": currency_code,
        "timezone": timezone,
    }

    return model_representation

