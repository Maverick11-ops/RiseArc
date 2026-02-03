from typing import Dict



def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def build_summary_prompt(
    profile: Dict[str, float],
    scenario: Dict[str, float],
    metrics: Dict[str, float],
    alert: str,
    savings_total: float,
    timeline_stats: Dict[str, float],
    job_stability_value: str,
    job_stability_weight: float,
) -> str:
    return f"""
You are RiseArc, a financial assistant powered by Nemotron-3-Nano.
Generate a concise, practical summary based on the user's profile and scenario.

Return in this format:
Summary:
- ...
- ...
- ...
Actions:
- ...
- ...
- ...
Warnings:
- ...

User Profile:
- Monthly income: {format_currency(profile['income_monthly'])}
- Monthly expenses: {format_currency(profile['expenses_monthly'])}
- Savings: {format_currency(profile['savings'])}
- Total debt: {format_currency(profile['debt'])}
- Industry: {profile['industry']}
- Job stability: {job_stability_value} (weight {job_stability_weight:+.0f})
- Dependents: {profile['dependents']}

Scenario:
- Months unemployed: {scenario['months_unemployed']:.0f}
- Expense cut: {scenario['expense_cut_pct']:.0f}%
- Severance: {format_currency(scenario['severance'])}

Computed Metrics:
- Runway (months): {metrics['runway_months']:.1f}
- Risk score (0-100): {metrics['risk_score']:.0f}
- Adjusted risk score (0-100): {metrics['adjusted_risk_score']:.0f}
- Debt ratio: {metrics['debt_ratio']:.2f}
- Monthly expenses after cut: {format_currency(metrics['monthly_expenses_cut'])}
- Estimated savings leaks (monthly): {format_currency(savings_total)}
- Timeline signals: months_until_zero={timeline_stats['months_until_zero']:.0f}, max_drawdown={format_currency(timeline_stats['max_drawdown'])}, trend_slope={format_currency(timeline_stats['trend_slope'])}

Alert Context:
{alert}
""".strip()
