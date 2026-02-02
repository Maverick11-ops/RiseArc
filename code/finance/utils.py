def safe_div(a, b, default=None):
    try:
        return a / b
    except Exception:
        return default

def round_or_none(v, ndigits=2):
    if v is None:
        return None
    return round(v, ndigits)

def validate_input(payload: dict):
    # minimal validation, returns tuple (income, expenses, savings)
    income = float(payload.get("income", 0.0))
    expenses = float(payload.get("expenses", 0.0))
    savings = float(payload.get("savings", 0.0))
    return income, expenses, savings
