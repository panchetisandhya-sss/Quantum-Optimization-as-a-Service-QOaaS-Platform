"""
Phase 1 tests — Security & International-Readiness.

Run with:
  cd /home/rgukt/.gemini/antigravity/scratch/qoaas-platform/backend
  python -m pytest test_phase1.py -v
"""
import os
import sys
import pytest

# ---------------------------------------------------------------------------
# 1. Solver label honesty
# ---------------------------------------------------------------------------
import numpy as np
from app.services.quantum import execute_optimization


def test_solver_label_small():
    """n <= 10: must report local NumPy QAOA, not Qiskit Aer."""
    Q = np.diag([-1.0, -2.0, -1.5])
    _, _, label = execute_optimization(Q)
    assert "NumPy QAOA" in label
    assert "Qiskit Aer" not in label
    assert "Local" in label


def test_solver_label_medium():
    """10 < n <= 32: still NumPy, not Qiskit Aer Emulator."""
    Q = np.eye(20) * -1.0
    _, _, label = execute_optimization(Q)
    assert "NumPy QAOA" in label
    assert "Qiskit Aer" not in label


def test_solver_label_large():
    """n > 32: classical decomposition, no QPU label."""
    Q = np.eye(40) * -1.0
    _, _, label = execute_optimization(Q)
    assert "Classical" in label or "Decomposition" in label
    assert "Qiskit Aer" not in label
    assert "QPU" not in label


# ---------------------------------------------------------------------------
# 2. Admin allow-list (no auto-admin via email domain)
# ---------------------------------------------------------------------------
from app.config import Settings  # import class, not singleton


def test_admin_email_domain_does_not_grant_admin():
    """@qoaas-platform.com email must NOT auto-grant admin when not in allow-list."""
    s = Settings(ADMIN_EMAILS="")
    admin_emails = s.get_admin_emails()
    assert "admin@qoaas-platform.com" not in admin_emails


def test_admin_email_allowlist_grants_admin():
    """Email in ADMIN_EMAILS env var must appear in the allow-list."""
    s = Settings(ADMIN_EMAILS="boss@company.com,cto@company.com")
    admin_emails = s.get_admin_emails()
    assert "boss@company.com" in admin_emails
    assert "cto@company.com" in admin_emails


def test_admin_email_allowlist_case_insensitive():
    """Allow-list matching must be case-insensitive."""
    s = Settings(ADMIN_EMAILS="Boss@Company.COM")
    admin_emails = s.get_admin_emails()
    assert "boss@company.com" in admin_emails


def test_non_admin_email_not_in_allowlist():
    """Regular user email must not appear in the admin allow-list."""
    s = Settings(ADMIN_EMAILS="boss@company.com")
    admin_emails = s.get_admin_emails()
    assert "user@example.com" not in admin_emails


# ---------------------------------------------------------------------------
# 3. CORS origins parsing
# ---------------------------------------------------------------------------
def test_cors_origins_single():
    s = Settings(CORS_ORIGINS="http://localhost:3000")
    assert s.get_cors_origins() == ["http://localhost:3000"]


def test_cors_origins_multiple():
    s = Settings(CORS_ORIGINS="http://localhost:3000,https://app.qoaas.com")
    origins = s.get_cors_origins()
    assert "http://localhost:3000" in origins
    assert "https://app.qoaas.com" in origins
    assert len(origins) == 2


def test_cors_origins_strips_spaces():
    s = Settings(CORS_ORIGINS="http://localhost:3000 , https://app.qoaas.com ")
    origins = s.get_cors_origins()
    assert all(" " not in o for o in origins)


# ---------------------------------------------------------------------------
# 4. Currency formatting
# ---------------------------------------------------------------------------
from app.services.ai import _format_currency


def test_currency_format_usd():
    assert _format_currency(1234.56, "USD") == "$1,234.56"


def test_currency_format_eur():
    assert _format_currency(1234.56, "EUR") == "€1,234.56"


def test_currency_format_inr():
    assert _format_currency(1234.56, "INR") == "₹1,234.56"


def test_currency_format_unknown_fallback():
    result = _format_currency(1234.56, "BRL")
    assert "BRL" in result
    assert "1,234.56" in result


# ---------------------------------------------------------------------------
# 5. i18n fields propagated through modeling
# ---------------------------------------------------------------------------
from app.services.modeling import parse_and_model_portfolio, parse_and_model_staffing


def test_portfolio_model_carries_currency():
    data = {
        "assets": [{"asset": "AAPL", "return": 0.1, "risk": 0.05}],
        "currency_code": "EUR",
        "timezone": "Europe/Berlin",
    }
    model = parse_and_model_portfolio(data)
    assert model["currency_code"] == "EUR"
    assert model["timezone"] == "Europe/Berlin"


def test_portfolio_model_defaults_currency():
    data = {"assets": [{"asset": "AAPL", "return": 0.1, "risk": 0.05}]}
    model = parse_and_model_portfolio(data)
    assert model["currency_code"] == "USD"  # DEFAULT_CURRENCY


def test_staffing_model_carries_currency():
    data = {
        "employees": [{"name": "Alice", "hourly_rate": 30, "skills": ["cs"], "availability": ["s1"]}],
        "shifts": [{"id": "s1", "name": "Morning", "demand": 1}],
        "currency_code": "GBP",
        "timezone": "Europe/London",
    }
    model = parse_and_model_staffing(data)
    assert model["currency_code"] == "GBP"
    assert model["timezone"] == "Europe/London"
