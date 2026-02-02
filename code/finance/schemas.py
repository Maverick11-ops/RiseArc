from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class SimulationInput:
    income: float
    expenses: float
    savings: float
    shock_income_factor: float = 0.8
    shock_expense_factor: float = 1.2
    debt: Optional[Dict[str, Any]] = None

# Outputs are plain dicts; dataclasses used for typing only.
