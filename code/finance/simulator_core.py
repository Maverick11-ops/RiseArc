from typing import Optional
from .schemas import SimulationInput

def compute_runway(income: float, expenses: float, savings: float) -> Optional[float]:
    net = income - expenses
    if net >= 0:
        return None
    burn = abs(net)
    if burn == 0:
        return None
    return round(savings / burn, 2)

def compute_metrics(sim: SimulationInput) -> dict:
    base = compute_runway(sim.income, sim.expenses, sim.savings)
    net = round(sim.income - sim.expenses, 2)
    burn = round(abs(net), 2) if net < 0 else 0.0
    return {"base_runway_months": base, "net_monthly": net, "burn_rate": burn}

def classify_status(runway: Optional[float]) -> str:
    if runway is None:
        return "stable"
    if runway >= 12:
        return "stable"
    if runway >= 6:
        return "watch"
    if runway >= 3:
        return "at_risk"
    return "critical"
