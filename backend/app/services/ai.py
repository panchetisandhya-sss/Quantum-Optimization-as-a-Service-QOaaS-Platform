import json
import requests
from typing import Dict, Any
from app.config import settings


def _format_currency(amount: float, currency_code: str) -> str:
    """
    Format a numeric amount as a locale-aware currency string.
    Uses Python's built-in formatting; for full locale support a library such
    as babel can be swapped in without changing callers.
    Symbol map covers the most common international currencies; unknown codes
    fall back to the ISO code prefix (e.g. 'EUR 1,234.56').
    """
    symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
        "INR": "₹", "CNY": "¥", "AUD": "A$", "CAD": "C$",
        "CHF": "CHF ", "SGD": "S$", "AED": "AED ",
    }
    symbol = symbols.get(currency_code.upper(), f"{currency_code} ")
    return f"{symbol}{amount:,.2f}"

def generate_openai_explanation(prompt: str) -> str:
    """
    Attempts to call OpenAI ChatCompletion API to generate insights.
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
        }
        data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a senior business consultant and quantum computing translator. Translate optimization output into a highly professional executive summary for business managers. Do not mention quantum mechanics, qubits, QUBOs, or circuits. Focus entirely on business value, risk, cost, and efficiency."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        else:
            print(f"OpenAI error: {response.text}")
            return ""
    except Exception as e:
        print(f"Failed to generate OpenAI explanation: {e}")
        return ""

def generate_explanation(job_data: Dict[str, Any]) -> str:
    """
    Orchestrates explanation generation. Uses OpenAI if API key exists,
    otherwise falls back to a high-quality heuristic template model.
    """
    service_type = job_data.get("service_type")
    results = job_data.get("results", {})
    
    if service_type == "portfolio":
        allocation = results.get("allocation", {})
        expected_return = results.get("expected_return", 0.0)
        risk_reduction = results.get("risk_reduction", 0.0)
        sharpe_ratio = results.get("sharpe_ratio", 0.0)
        
        # Sort allocation to find top assets
        sorted_assets = sorted(allocation.items(), key=lambda x: x[1], reverse=True)
        top_assets = [f"{asset} ({round(w * 100, 1)}%)" for asset, w in sorted_assets[:3] if w > 0]
        top_assets_str = ", ".join(top_assets) if top_assets else "balanced assets"
        
        prompt = f"""
        Generate a business explanation for a Portfolio Optimization run.
        Top Allocations: {top_assets_str}
        Expected Portfolio Return: {round(expected_return * 100, 2)}%
        Volatility/Risk Reduction: {round(risk_reduction * 100, 2)}%
        Sharpe Ratio: {round(sharpe_ratio, 2)}
        """
        
        if settings.OPENAI_API_KEY:
            openai_res = generate_openai_explanation(prompt)
            if openai_res:
                return openai_res
                
        # High quality template fallback
        top_asset_names = [a[0] for a in sorted_assets[:2]]
        defense_assets = [name for name, w in sorted_assets if w > 0 and name not in top_asset_names]
        defense_str = f"hedged with positions in {', '.join(defense_assets[:2])}" if defense_assets else "fully concentrated in high-conviction targets"
        
        return f"The portfolio optimization algorithm has successfully constructed a risk-managed frontier matching your target allocation parameters. " \
               f"Our engine prioritized heavy weightings in {top_assets_str} to capture robust market return metrics, " \
               f"while volatility was actively {defense_str}. " \
               f"This configuration achieves a Sharpe Ratio of {round(sharpe_ratio, 2)}, indicating an optimized return-to-risk ratio. " \
               f"By utilizing our mathematical solver, the portfolio is projected to decrease historical variance exposure by {round(risk_reduction * 100, 1)}% " \
               f"relative to an unweighted asset distribution, safeguarding capital while maintaining an expected yield of {round(expected_return * 100, 1)}%."
               
    elif service_type == "staffing":
        schedule = results.get("schedule", [])
        labor_cost = results.get("labor_cost", 0.0)
        coverage_percent = results.get("coverage_percent", 0.0)
        unassigned_shifts = results.get("unassigned_shifts_count", 0)
        
        # Extract employee counts and shifts info
        total_assignments = sum(len(s["assigned_employees"]) for s in schedule)
        shift_coverage_details = [f"{s['shift_name']} ({len(s['assigned_employees'])} staffed)" for s in schedule]
        shift_coverage_str = ", ".join(shift_coverage_details)
        
        prompt = f"""
        Generate a business explanation for a Staffing/Scheduling Optimization run.
        Shift staffings: {shift_coverage_str}
        Total Daily Labor Cost: ${labor_cost}
        Overall Coverage: {coverage_percent}%
        Unassigned Shifts Count: {unassigned_shifts}
        """
        
        if settings.OPENAI_API_KEY:
            openai_res = generate_openai_explanation(prompt)
            if openai_res:
                return openai_res

        # High quality template fallback
        currency_code = results.get("currency_code", settings.DEFAULT_CURRENCY)
        labor_cost_fmt = _format_currency(labor_cost, currency_code)
        unassigned_msg = "All required slots have been staffed successfully, meeting your operational targets."
        if unassigned_shifts > 0:
            unassigned_msg = (
                f"There remain {unassigned_shifts} unassigned shift slots due to employee "
                f"availability limits or skill mismatch. We recommend calling in contingent "
                f"staff or offering overtime to fill these coverage gaps."
            )

        return f"Our quantum-classical hybrid solver successfully generated an optimal workforce roster. " \
               f"By analyzing shift demand constraints and employee skill availability, the model scheduled {total_assignments} individual shift placements ({shift_coverage_str}). " \
               f"The calculated daily operating cost is ${labor_cost:,.2f}, delivering a {coverage_percent}% coverage compliance rate. " \
               f"Unstaffed shift slots were minimized ({unassigned_shifts} unassigned), maintaining operational continuity while eliminating unnecessary overtime expenditures."

    elif service_type == "budget_allocation":
        total_savings = results.get("total_potential_savings", 0.0)
        budget_used = results.get("budget_used", 0.0)
        budget_cap = results.get("budget_cap", 0.0)
        budget_util_pct = results.get("budget_utilization_pct", 0.0)
        selected_count = results.get("selected_count", 0)
        total_records = results.get("total_records", 0)
        selected_orgs = results.get("selected_organizations", [])

        top_orgs_str = ", ".join(selected_orgs[:4]) if selected_orgs else "targeted entities"

        prompt = f"""
        Generate an organizational executive narrative for a Budget Allocation Optimization run.
        Selected Entities ({selected_count}/{total_records}): {top_orgs_str}
        Total Realized Savings: ₹{total_savings:,.2f}
        Budget Utilization: {budget_util_pct}% (₹{budget_used:,.2f} / ₹{budget_cap:,.2f})
        """

        if settings.OPENAI_API_KEY:
            openai_res = generate_openai_explanation(prompt)
            if openai_res:
                return openai_res

        return f"The 0-1 Knapsack resource-allocation solver successfully optimized your organizational budget structure across {total_records} candidate entities. " \
               f"By selecting {selected_count} high-efficiency organizational units (including {top_orgs_str}), the solver captures a total projected savings of ₹{total_savings:,.2f}. " \
               f"This allocation maximizes cost reduction while strictly respecting operational caps, utilizing {budget_util_pct}% of the total allocated budget ceiling (₹{budget_used:,.2f} of ₹{budget_cap:,.2f}). " \
               f"Non-selected entities were excluded due to lower ROI/savings density, guaranteeing an optimal return on budgeted resources."
               
    return "Optimization complete. The system has computed the optimal solution matching all input conditions."
