from typing import Dict, Any, Tuple, List
import numpy as np

def generate_portfolio_qubo(model: Dict[str, Any], num_bits: int = 3) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Converts continuous portfolio optimization variables to binary variables.
    Approximates weight w_i = sum_{k=0}^{num_bits-1} 2^{-(k+1)} * x_{i, k}
    Subject to: sum_i w_i = 1  (Budget constraint)
    Objective: Minimize risk - lambda * expected_return
    """
    names = model["raw_names"]
    returns = model["returns"]
    cov = np.array(model["covariance"])
    risk_aversion = model["risk_aversion"]
    num_assets = len(names)
    
    # Binary variables count
    total_vars = num_assets * num_bits
    
    # Mapping from binary index to asset details
    mapping = []
    for idx_asset in range(num_assets):
        for bit in range(num_bits):
            coef = 2.0 ** -(bit + 1)
            mapping.append({
                "binary_index": idx_asset * num_bits + bit,
                "asset_index": idx_asset,
                "asset_name": names[idx_asset],
                "bit_weight": coef
            })
            
    # Initialize QUBO Matrix Q (size total_vars x total_vars)
    # H(x) = x^T Q x
    Q = np.zeros((total_vars, total_vars))
    
    # 1. Objective function: Minimize Risk - Lambda * Return
    # Risk term: sum_{i,j} w_i * w_j * cov_{i,j}
    # Return term: - lambda * sum_i w_i * returns_i
    for idx_i in range(num_assets):
        for idx_j in range(num_assets):
            cov_val = cov[idx_i, idx_j]
            for bit_k in range(num_bits):
                var_i = idx_i * num_bits + bit_k
                coef_k = 2.0 ** -(bit_k + 1)
                
                # Risk contributions
                for bit_m in range(num_bits):
                    var_j = idx_j * num_bits + bit_m
                    coef_m = 2.0 ** -(bit_m + 1)
                    Q[var_i, var_j] += coef_k * coef_m * cov_val
                    
        # Return contributions (Linear terms go on the diagonal of Q)
        for bit_k in range(num_bits):
            var_i = idx_i * num_bits + bit_k
            coef_k = 2.0 ** -(bit_k + 1)
            Q[var_i, var_i] -= risk_aversion * coef_k * returns[idx_i]
            
    # 2. Penalty constraint: P * (sum_i w_i - 1)^2
    # P * (sum_{i, k} coef_k * x_{i,k} - 1)^2
    # = P * [ sum_{i,k} sum_{j,m} coef_k * coef_m * x_{i,k} * x_{j,m} - 2 * sum_{i,k} coef_k * x_{i,k} + 1 ]
    # Choose penalty factor P based on returns and risk scales (typically 2 to 5 times max coeff)
    max_return = max(returns) if returns else 1.0
    penalty_factor = 2.5 * max(max_return, 1.0)
    
    for idx_i in range(num_assets):
        for bit_k in range(num_bits):
            var_i = idx_i * num_bits + bit_k
            coef_k = 2.0 ** -(bit_k + 1)
            
            # Linear penalty contribution
            Q[var_i, var_i] -= 2.0 * penalty_factor * coef_k
            
            # Quadratic penalty contribution
            for idx_j in range(num_assets):
                for bit_m in range(num_bits):
                    var_j = idx_j * num_bits + bit_m
                    coef_m = 2.0 ** -(bit_m + 1)
                    Q[var_i, var_j] += penalty_factor * coef_k * coef_m
                    
    return Q, mapping

def generate_staffing_qubo(model: Dict[str, Any]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Converts staffing scheduling into QUBO.
    Decision variables: x_{e, s} are already binary.
    Constraints:
      1. Under/over staffing penalty: P_demand * (sum_e x_{e,s} - D_s)^2 for each shift s
      2. Max shift penalty: P_max * sum_{s1 < s2} x_{e, s1} * x_{e, s2} for each employee e
      3. Availability: P_avail * x_{e,s} if shift s is not in employee availability list
    Objective: Minimize cost: sum_{e,s} C_e * x_{e,s}
    """
    variables = model["variables"]
    total_vars = len(variables)
    
    # Construct mapping index to variable metadata
    mapping = []
    for idx, var in enumerate(variables):
        mapping.append({
            "binary_index": idx,
            "employee_id": var["employee_id"],
            "employee_name": var["employee_name"],
            "shift_id": var["shift_id"],
            "shift_name": var["shift_name"],
            "is_available": var["is_available"],
            "cost": var["cost"]
        })
        
    Q = np.zeros((total_vars, total_vars))
    
    # 1. Objective function: Minimize sum_{e,s} C_e * x_{e,s}
    for idx, var in enumerate(mapping):
        Q[idx, idx] += var["cost"]
        
    # 2. Availability penalty (if not available, add heavy penalty on the diagonal)
    penalty_avail = 500.0
    for idx, var in enumerate(mapping):
        if not var["is_available"]:
            Q[idx, idx] += penalty_avail
            
    # 3. Max Shift Penalty: at most 1 shift per employee
    # P_max * sum_{s1 < s2} x_{e, s1} * x_{e, s2}
    penalty_max_shifts = 300.0
    for idx_i, var_i in enumerate(mapping):
        for idx_j, var_j in enumerate(mapping):
            if idx_i < idx_j:
                # Same employee, different shifts
                if var_i["employee_id"] == var_j["employee_id"]:
                    Q[idx_i, idx_j] += penalty_max_shifts
                    Q[idx_j, idx_i] += penalty_max_shifts  # Maintain symmetric properties
                    
    # 4. Shift Demand Penalty: P_demand * (sum_e x_{e,s} - D_s)^2
    # = P_demand * [ sum_{e1, e2} x_{e1, s} * x_{e2, s} - 2 * D_s * sum_e x_{e,s} + D_s^2 ]
    penalty_demand = 200.0
    for shift in model["shifts"]:
        shift_id = shift["id"]
        demand = shift["demand"]
        
        # Get variables related to this shift
        shift_var_indices = [idx for idx, var in enumerate(mapping) if var["shift_id"] == shift_id]
        
        # Apply demand penalties
        for idx_i in shift_var_indices:
            # Linear term: - 2 * D_s * P_demand
            Q[idx_i, idx_i] -= 2.0 * demand * penalty_demand
            
            # Quadratic term: P_demand * x_{e1,s} * x_{e2,s}
            for idx_j in shift_var_indices:
                Q[idx_i, idx_j] += penalty_demand
                
    return Q, mapping


def generate_budget_allocation_qubo(model: Dict[str, Any]) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Converts 0-1 Knapsack Organizational Budget Allocation into QUBO matrix.
    Decision variables x_i ∈ {0,1} (1 = Select entity/org, 0 = Do not select)
    Objective: Maximize realized potential savings (min -sum_i S_i * x_i)
    Constraints:
      1. Budget penalty: P_budget * max(0, sum_i B_i * x_i - B_max)^2
      2. Headcount penalty: P_headcount * max(0, sum_i H_i * x_i - H_max)^2
    """
    variables = model["variables"]
    total_vars = len(variables)
    savings = np.array(model["savings_vector"])
    budgets = np.array(model["budget_vector"])
    headcount = np.array(model["headcount_vector"])
    max_budget = float(model["max_budget"])
    max_headcount = float(model["max_headcount"])

    mapping = []
    for idx, var in enumerate(variables):
        mapping.append({
            "binary_index": idx,
            "record_id": var["record_id"],
            "budget": var["budget"],
            "potential_savings": var["potential_savings"],
            "headcount": var["headcount"],
            "actual_expense": var["actual_expense"],
            "revenue": var["revenue"]
        })

    Q = np.zeros((total_vars, total_vars))

    # 1. Objective: Min -sum_i Savings_i * x_i
    for idx in range(total_vars):
        Q[idx, idx] -= savings[idx]

    # Dynamic penalty scaling based on max savings scale
    max_savings = float(np.max(savings)) if len(savings) > 0 else 1.0
    
    # Penalty parameters relative to scale
    total_b_sum = float(np.sum(budgets)) if np.sum(budgets) > 0 else 1.0
    penalty_b = (max_savings * 3.0) / (total_b_sum ** 2) if total_b_sum > 0 else 1.0

    total_h_sum = float(np.sum(headcount)) if np.sum(headcount) > 0 else 1.0
    penalty_h = (max_savings * 2.0) / (total_h_sum ** 2) if total_h_sum > 0 else 1.0

    # Apply soft penalty terms for capacity / budget bounds
    for i in range(total_vars):
        # Linear penalty terms: -2 * B_max * P_b * B_i
        Q[i, i] -= 2.0 * max_budget * penalty_b * budgets[i]
        Q[i, i] -= 2.0 * max_headcount * penalty_h * headcount[i]

        for j in range(total_vars):
            # Quadratic penalty terms: P_b * B_i * B_j
            Q[i, j] += penalty_b * budgets[i] * budgets[j]
            Q[i, j] += penalty_h * headcount[i] * headcount[j]

    return Q, mapping

