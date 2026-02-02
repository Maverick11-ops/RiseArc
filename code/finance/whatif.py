from typing import List, Dict, Any, Optional
from .schemas import SimulationInput
from .simulator_core import compute_metrics, classify_status
from .debt import compute_debt_monthly_payment, apply_debt_to_cashflow

def generate_default_scenarios() -> List[Dict[str, Any]]:
    return [
        {"name": "baseline", "income_factor": 1.0, "expense_factor": 1.0},
        {"name": "expense_plus_20", "income_factor": 1.0, "expense_factor": 1.2},
        {"name": "income_minus_20", "income_factor": 0.8, "expense_factor": 1.0},
        {"name": "combined_shock", "income_factor": 0.8, "expense_factor": 1.2},
        {"name": "job_loss", "income_factor": 0.0, "expense_factor": 1.0},
    ]

def run_scenarios(income: float, expenses: float, savings: float,
                  custom_scenarios: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    defs = generate_default_scenarios()
    if custom_scenarios:
        defs.extend(custom_scenarios)
    baseline_input = SimulationInput(income, expenses, savings)
    baseline_metrics = compute_metrics(baseline_input)
    baseline_status = classify_status(baseline_metrics["base_runway_months"])
    baseline_result = {"metrics": baseline_metrics, "status_code": baseline_status, "action_codes": [] , "input": baseline_input.__dict__}
    scenarios_out = []
    for d in defs:
        inc = income * d.get("income_factor", 1.0)
        exp = expenses * d.get("expense_factor", 1.0)
        sim_in = SimulationInput(inc, exp, savings)
        metrics = compute_metrics(sim_in)
        status = classify_status(metrics["base_runway_months"])
        # simple delta
        base_runway = baseline_metrics["base_runway_months"]
        sc_runway = metrics["base_runway_months"]
        delta = None
        try:
            if base_runway is None and sc_runway is None:
                delta = 0.0
            elif base_runway is None:
                delta = -1.0
            elif sc_runway is None:
                delta = 1.0
            else:
                delta = round((sc_runway - base_runway) / max(abs(base_runway), 1e-9), 3)
        except Exception:
            delta = None
        scenarios_out.append({"name": d["name"], "params": {"income_factor": d["income_factor"], "expense_factor": d["expense_factor"]}, "result": {"metrics": metrics, "status_code": status}, "delta": {"runway_change_pct": delta}})
    return {"baseline": baseline_result, "scenarios": scenarios_out, "metadata": {"count": len(scenarios_out)}}
