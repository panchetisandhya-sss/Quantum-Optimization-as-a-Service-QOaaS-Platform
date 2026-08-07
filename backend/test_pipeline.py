import numpy as np
from app.services.modeling import parse_and_model_portfolio, parse_and_model_staffing
from app.services.qubo import generate_portfolio_qubo, generate_staffing_qubo
from app.services.quantum import execute_optimization, repair_portfolio_allocation

def test_portfolio_modeling_and_qubo():
    # 1. Test data modeling
    test_data = {
        "assets": [
            {"asset": "AAPL", "return": 0.12, "risk": 0.08},
            {"asset": "MSFT", "return": 0.10, "risk": 0.06}
        ],
        "risk_aversion": 0.5
    }
    model = parse_and_model_portfolio(test_data)
    assert model["service_type"] == "portfolio"
    assert model["num_variables"] == 2
    assert len(model["returns"]) == 2
    
    # 2. Test QUBO compiler
    # w_i represented by 3 bits -> 2 assets * 3 = 6 binary variables
    Q, mapping = generate_portfolio_qubo(model, num_bits=3)
    assert Q.shape == (6, 6)
    assert len(mapping) == 6
    
    # Check that diagonal and off-diagonal entries contain non-zero weights
    assert np.any(Q)

def test_staffing_modeling_and_qubo():
    test_data = {
        "employees": [
            {"name": "Alice", "hourly_rate": 30.0, "skills": ["support"], "availability": ["shift_1"]}
        ],
        "shifts": [
            {"id": "shift_1", "name": "Shift 1", "demand": 1}
        ]
    }
    model = parse_and_model_staffing(test_data)
    assert model["service_type"] == "staffing"
    assert model["num_variables"] == 1
    
    Q, mapping = generate_staffing_qubo(model)
    assert Q.shape == (1, 1)
    assert len(mapping) == 1

def test_quantum_solver_and_repair():
    # Construct a tiny 3x3 QUBO matrix
    Q = np.array([
        [-5.0, 2.0, 1.0],
        [2.0, -3.0, 1.5],
        [1.0, 1.5, -4.0]
    ])
    sol_bits, energy, solver_name = execute_optimization(Q)
    assert len(sol_bits) == 3
    assert sol_bits.dtype == int
    assert isinstance(energy, float)
    assert "Quantum" in solver_name

    # Test portfolio constraint repair
    mapping = [
        {"asset_name": "AAPL", "bit_weight": 0.5},
        {"asset_name": "AAPL", "bit_weight": 0.25},
        {"asset_name": "MSFT", "bit_weight": 0.5}
    ]
    # Say solver outputs bits [1, 0, 1] -> AAPL weight = 0.5, MSFT weight = 0.5
    sol_bits = np.array([1, 0, 1])
    repaired = repair_portfolio_allocation(sol_bits, mapping)
    assert repaired["allocation"]["AAPL"] == 0.5
    assert repaired["allocation"]["MSFT"] == 0.5
    assert abs(sum(repaired["allocation"].values()) - 1.0) < 1e-4
