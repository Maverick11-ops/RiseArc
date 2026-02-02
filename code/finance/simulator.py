# app/finance/simulator.py
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SimulationInput:
    income: float
    expenses: float
    savings: float
    shock_expense_factor: float = 1.2
    shock_income_factor: float = 0.8


def _compute_runway_months(income: float, expenses: float, savings: float) -> float:
    net = income - expenses
    if net >= 0:
        return float("inf")
    burn = abs(net)
    if burn == 0:
        return float("inf")
    return savings / burn


def _classify_status(runway_months: float) -> str:
    if runway_months == float("inf"):
        return "stable"
    if runway_months >= 12:
        return "stable"
    if runway_months >= 6:
        return "watch"
    if runway_months >= 3:
        return "at_risk"
    return "critical"


def _severity_from_runway(runway_months: float) -> float:
    if runway_months == float("inf"):
        return 0.0
    if runway_months >= 12:
        return 0.1
    if runway_months >= 6:
        return 0.3
    if runway_months >= 3:
        return 0.6
    if runway_months > 0:
        return 0.9
    return 1.0


def _suggest_action_codes(net: float, base_runway: float, shocked_runway: float) -> List[str]:
    codes: List[str] = []
    if net < 0:
        codes.append("reduce_expenses")
        codes.append("increase_income")
    if base_runway != float("inf") and base_runway < 6:
        codes.append("build_savings")
    if shocked_runway != float("inf") and base_runway != float("inf"):
        if shocked_runway / max(base_runway, 1e-9) < 0.5:
            codes.append("stress_test_plans")
    if base_runway != float("inf") and base_runway < 3:
        codes.append("prioritize_liquidity")
        codes.append("debt_refinance")
    seen = set()
    out = []
    for c in codes:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _percent_change(a: float, b: float) -> Optional[float]:
    if a == float("inf") and b == float("inf"):
        return 0.0
    if a == float("inf"):
        return 1.0
    if b == float("inf"):
        return -1.0
    if a == 0:
        return None if b == 0 else float("inf")
    return (b - a) / abs(a)


def _single_run(income: float, expenses: float, savings: float) -> Dict[str, Any]:
    base_runway = _compute_runway_months(income, expenses, savings)
    net_monthly = income - expenses
    burn_rate = abs(net_monthly) if net_monthly < 0 else 0.0
    status_code = _classify_status(base_runway)
    severity = _severity_from_runway(base_runway)
    action_codes = _suggest_action_codes(net_monthly, base_runway, base_runway)
    return {
        "metrics": {
            "runway_months": None if base_runway == float("inf") else round(base_runway, 2),
            "net_monthly": round(net_monthly, 2),
            "burn_rate": round(burn_rate, 2),
        },
        "status": {
            "status_code": status_code,
            "severity": round(severity, 3),
        },
        "actions": {"action_codes": action_codes},
    }


def run_simulation(
    income: float,
    expenses: float,
    savings: float,
    shock_expense_factor: float = 1.2,
    shock_income_factor: float = 0.8,
) -> Dict[str, Any]:
    sim = SimulationInput(
        income=income,
        expenses=expenses,
        savings=savings,
        shock_expense_factor=shock_expense_factor,
        shock_income_factor=shock_income_factor,
    )

    base_runway = _compute_runway_months(sim.income, sim.expenses, sim.savings)
    shocked_income = sim.income * sim.shock_income_factor
    shocked_expenses = sim.expenses * sim.shock_expense_factor
    shocked_runway = _compute_runway_months(shocked_income, shocked_expenses, sim.savings)

    net_monthly = sim.income - sim.expenses
    burn_rate = abs(net_monthly) if net_monthly < 0 else 0.0
    sensitivity = _percent_change(base_runway, shocked_runway)

    status_code = _classify_status(base_runway if base_runway != float("inf") else shocked_runway)
    severity = _severity_from_runway(base_runway if base_runway != float("inf") else shocked_runway)
    action_codes = _suggest_action_codes(net_monthly, base_runway, shocked_runway)

    result = {
        "metrics": {
            "base_runway_months": None if base_runway == float("inf") else round(base_runway, 2),
            "shocked_runway_months": None if shocked_runway == float("inf") else round(shocked_runway, 2),
            "net_monthly": round(net_monthly, 2),
            "burn_rate": round(burn_rate, 2),
            "sensitivity": None if sensitivity is None or sensitivity == float("inf") else round(sensitivity, 3),
        },
        "status": {
            "status_code": status_code,
            "severity": round(severity, 3),
        },
        "actions": {"action_codes": action_codes},
        "input": asdict(sim),
        "metadata": {"timestamp": datetime.utcnow().isoformat() + "Z", "note": "structured output only"},
    }
    return result


def generate_what_if_scenarios(
    income: float,
    expenses: float,
    savings: float,
    custom_scenarios: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Produce a set of machine-readable what-if scenarios.
    Returns:
      {
        "baseline": {...},
        "scenarios": [
          {"name": "...", "params": {...}, "metrics": {...}, "status": {...}, "actions": {...}, "delta": {...}},
          ...
        ],
        "metadata": {...}
      }
    """
    baseline = run_simulation(income, expenses, savings)
    base_runway = baseline["metrics"]["base_runway_months"]

    # default scenario definitions
    defs = [
        {"name": "expense_plus_20", "income_factor": 1.0, "expense_factor": 1.2},
        {"name": "income_minus_20", "income_factor": 0.8, "expense_factor": 1.0},
        {"name": "combined_shock", "income_factor": 0.8, "expense_factor": 1.2},
        {"name": "job_loss", "income_factor": 0.0, "expense_factor": 1.0},
        {"name": "expense_spike_50", "income_factor": 1.0, "expense_factor": 1.5},
    ]

    if custom_scenarios:
        # custom scenarios can override or extend defaults; expected keys: name, income_factor, expense_factor
        defs.extend(custom_scenarios)

    scenarios_out: List[Dict[str, Any]] = []
    for d in defs:
        inc = income * d.get("income_factor", 1.0)
        exp = expenses * d.get("expense_factor", 1.0)
        single = _single_run(inc, exp, savings)

        # compute shocked runway using same helpers for comparability
        shocked_runway = single["metrics"]["runway_months"]
        # delta vs baseline (percent change)
        delta_runway = None
        if base_runway is None and shocked_runway is None:
            delta_runway = 0.0
        elif base_runway is None and shocked_runway is not None:
            delta_runway = -1.0
        elif base_runway is not None and shocked_runway is None:
            delta_runway = 1.0
        else:
            try:
                delta_runway = _percent_change(base_runway, shocked_runway)
            except Exception:
                delta_runway = None

        scenarios_out.append({
            "name": d.get("name", "unnamed"),
            "params": {"income_factor": d.get("income_factor", 1.0), "expense_factor": d.get("expense_factor", 1.0)},
            "metrics": single["metrics"],
            "status": single["status"],
            "actions": single["actions"],
            "delta": {"runway_change_pct": None if delta_runway is None else round(delta_runway, 3)},
        })

    return {
        "baseline": baseline,
        "scenarios": scenarios_out,
        "metadata": {"generated_at": datetime.utcnow().isoformat() + "Z", "scenario_count": len(scenarios_out)},
    }
