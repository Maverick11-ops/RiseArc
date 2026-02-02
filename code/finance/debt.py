import math

def compute_debt_monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    if term_months <= 0 or principal <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return principal / term_months
    payment = principal * (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)
    return round(payment, 2)

def apply_debt_to_cashflow(net_monthly: float, debt_min_payment: float) -> float:
    return round(net_monthly - debt_min_payment, 2)
