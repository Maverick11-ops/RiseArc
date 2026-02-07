from typing import Dict, List

LLM_RUNWAY_MAX = 60.0
LLM_DEBT_RATIO_MAX = 3.0
LLM_RISK_MIN = 0.0
LLM_RISK_MAX = 100.0
LLM_INCOME_MAX = 200000.0
LLM_EXPENSES_MAX = 200000.0
LLM_SAVINGS_MAX = 2000000.0
LLM_DEBT_MAX = 2000000.0
LLM_DEPENDENTS_MAX = 10.0
LLM_UNEMPLOYED_MONTHS_MAX = 60.0
LLM_EXPENSE_CUT_MAX = 80.0
LLM_SEVERANCE_MAX = 200000.0
LLM_BENEFITS_MAX = 50000.0
LLM_OTHER_INCOME_MAX = 50000.0
LLM_INCOME_CHANGE_MAX = 50000.0
LLM_EXTRA_EXPENSES_MAX = 50000.0
LLM_ONE_TIME_MAX = 500000.0
LLM_SAVINGS_LEAKS_MAX = 50000.0
LLM_DRAWDOWN_MAX = 1000000.0
LLM_TREND_SLOPE_MAX = 200000.0

JOB_STABILITY_WEIGHTS = {
    "stable": -8.0,
    "medium": 4.0,
    "unstable": 12.0,
}
JOB_STABILITY_LABELS = {
    "stable": "Stable",
    "medium": "Medium",
    "unstable": "Unstable",
}


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


def normalize_job_stability(value: str) -> str:
    if not value:
        return "medium"
    cleaned = value.strip().lower()
    aliases = {
        "stable / full-time": "stable",
        "stable": "stable",
        "full-time": "stable",
        "full time": "stable",
        "medium": "medium",
        "contract / gig": "medium",
        "contract": "medium",
        "gig": "medium",
        "unstable": "unstable",
        "recently unemployed": "unstable",
        "unemployed": "unstable",
    }
    return aliases.get(cleaned, "medium")


def job_stability_weight(value: str) -> float:
    key = normalize_job_stability(value)
    return JOB_STABILITY_WEIGHTS.get(key, 0.0)


def job_stability_label(value: str) -> str:
    key = normalize_job_stability(value)
    return JOB_STABILITY_LABELS.get(key, "Medium")


def compute_runway(savings: float, monthly_expenses: float, severance: float) -> float:
    if monthly_expenses <= 0:
        return 0.0
    return (savings + severance) / monthly_expenses


def compute_debt_ratio(debt: float, income_monthly: float) -> float:
    annual_income = income_monthly * 12.0
    if annual_income <= 0:
        return 1.0
    return debt / annual_income


def compute_risk_score(
    runway_months: float,
    debt_ratio: float,
    job_stability: str,
    industry: str,
) -> float:
    score = 60.0

    if runway_months >= 12:
        score -= 30
    elif runway_months >= 6:
        score -= 20
    elif runway_months >= 3:
        score -= 10
    elif runway_months >= 1:
        score += 5
    else:
        score += 15

    score += clamp(debt_ratio * 50.0, 0.0, 20.0)

    score += job_stability_weight(job_stability)

    industry_adjust = {
        "Tech": 8,
        "Finance": 4,
        "Healthcare": -4,
        "Education": -2,
        "Retail": 6,
        "Manufacturing": 4,
        "Hospitality": 8,
        "Other": 2,
    }
    score += industry_adjust.get(industry, 2)

    return clamp(score, 0.0, 100.0)


def adjust_risk_for_scenario(
    base_score: float,
    runway_months: float,
    months_unemployed: float,
) -> float:
    if months_unemployed <= 0:
        return clamp(base_score - 5.0, 0.0, 100.0)
    gap = max(months_unemployed - runway_months, 0.0)
    cushion = max(runway_months - months_unemployed, 0.0)
    penalty = clamp(gap * 4.0, 0.0, 20.0)
    reduction = clamp(cushion * 1.5, 0.0, 10.0)
    return clamp(base_score + penalty - reduction, 0.0, 100.0)


def build_timeline(
    starting_savings: float,
    monthly_expenses: float,
    months: int,
    severance: float,
) -> List[float]:
    timeline = []
    balance = starting_savings + severance
    for _ in range(months + 1):
        timeline.append(round(balance, 2))
        balance -= monthly_expenses
    return timeline


def total_savings_leaks(costs: List[float]) -> float:
    return round(sum(costs), 2)


def compute_timeline_stats(timeline: List[float]) -> Dict[str, float]:
    if not timeline:
        return {"months_until_zero": 0.0, "max_drawdown": 0.0, "trend_slope": 0.0}
    months_until_zero = next((i for i, v in enumerate(timeline) if v <= 0), len(timeline) - 1)
    max_drawdown = max(timeline) - min(timeline)
    trend_slope = (timeline[-1] - timeline[0]) / max(len(timeline) - 1, 1)
    return {
        "months_until_zero": float(months_until_zero),
        "max_drawdown": float(max_drawdown),
        "trend_slope": float(trend_slope),
    }


def clamp_llm_metrics(metrics: Dict[str, float]) -> Dict[str, float]:
    return {
        "monthly_expenses_cut": clamp(metrics["monthly_expenses_cut"], 0.0, LLM_EXPENSES_MAX),
        "monthly_net_burn": clamp(metrics.get("monthly_net_burn", metrics["monthly_expenses_cut"]), -LLM_EXPENSES_MAX, LLM_EXPENSES_MAX),
        "monthly_support": clamp(metrics.get("monthly_support", 0.0), 0.0, LLM_OTHER_INCOME_MAX + LLM_BENEFITS_MAX),
        "one_time_expense": clamp(metrics.get("one_time_expense", 0.0), 0.0, LLM_ONE_TIME_MAX),
        "runway_months": clamp(metrics["runway_months"], 0.0, LLM_RUNWAY_MAX),
        "debt_ratio": clamp(metrics["debt_ratio"], 0.0, LLM_DEBT_RATIO_MAX),
        "risk_score": clamp(metrics["risk_score"], LLM_RISK_MIN, LLM_RISK_MAX),
        "adjusted_risk_score": clamp(metrics["adjusted_risk_score"], LLM_RISK_MIN, LLM_RISK_MAX),
    }


def clamp_llm_timeline_stats(stats: Dict[str, float]) -> Dict[str, float]:
    return {
        "months_until_zero": clamp(stats["months_until_zero"], 0.0, LLM_RUNWAY_MAX),
        "max_drawdown": clamp(stats["max_drawdown"], 0.0, LLM_DRAWDOWN_MAX),
        "trend_slope": clamp(stats["trend_slope"], -LLM_TREND_SLOPE_MAX, LLM_TREND_SLOPE_MAX),
    }


def clamp_llm_savings_total(value: float) -> float:
    return clamp(value, 0.0, LLM_SAVINGS_LEAKS_MAX)


def clamp_llm_profile(profile: Dict[str, float]) -> Dict[str, float]:
    return {
        "income_monthly": clamp(profile["income_monthly"], 0.0, LLM_INCOME_MAX),
        "expenses_monthly": clamp(profile["expenses_monthly"], 0.0, LLM_EXPENSES_MAX),
        "savings": clamp(profile["savings"], 0.0, LLM_SAVINGS_MAX),
        "debt": clamp(profile["debt"], 0.0, LLM_DEBT_MAX),
        "dependents": clamp(profile["dependents"], 0.0, LLM_DEPENDENTS_MAX),
        "industry": profile.get("industry", "Other"),
        "job_stability": profile.get("job_stability", "medium"),
    }


def clamp_llm_scenario(scenario: Dict[str, float]) -> Dict[str, float]:
    return {
        "months_unemployed": clamp(scenario["months_unemployed"], 0.0, LLM_UNEMPLOYED_MONTHS_MAX),
        "expense_cut_pct": clamp(scenario["expense_cut_pct"], 0.0, LLM_EXPENSE_CUT_MAX),
        "severance": clamp(scenario["severance"], 0.0, LLM_SEVERANCE_MAX),
        "unemployment_benefit_monthly": clamp(scenario.get("unemployment_benefit_monthly", 0.0), 0.0, LLM_BENEFITS_MAX),
        "other_income_monthly": clamp(scenario.get("other_income_monthly", 0.0), 0.0, LLM_OTHER_INCOME_MAX),
        "income_change_monthly": clamp(
            scenario.get("income_change_monthly", 0.0), -LLM_INCOME_CHANGE_MAX, LLM_INCOME_CHANGE_MAX
        ),
        "extra_monthly_expenses": clamp(scenario.get("extra_monthly_expenses", 0.0), 0.0, LLM_EXTRA_EXPENSES_MAX),
        "debt_payment_monthly": clamp(scenario.get("debt_payment_monthly", 0.0), 0.0, LLM_EXTRA_EXPENSES_MAX),
        "healthcare_monthly": clamp(scenario.get("healthcare_monthly", 0.0), 0.0, LLM_EXTRA_EXPENSES_MAX),
        "dependent_care_monthly": clamp(scenario.get("dependent_care_monthly", 0.0), 0.0, LLM_EXTRA_EXPENSES_MAX),
        "job_search_monthly": clamp(scenario.get("job_search_monthly", 0.0), 0.0, LLM_EXTRA_EXPENSES_MAX),
        "one_time_expense": clamp(scenario.get("one_time_expense", 0.0), 0.0, LLM_ONE_TIME_MAX),
        "one_time_income": clamp(scenario.get("one_time_income", 0.0), 0.0, LLM_ONE_TIME_MAX),
        "relocation_cost": clamp(scenario.get("relocation_cost", 0.0), 0.0, LLM_ONE_TIME_MAX),
    }
