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
    profile_debt_payment = float(profile.get("debt_payment_monthly", 0.0))
    total_required_outflow = float(profile.get("expenses_monthly", 0.0)) + profile_debt_payment
    monthly_addons_total = (
        scenario.get("extra_monthly_expenses", 0.0)
        + scenario.get("debt_payment_monthly", 0.0)
        + scenario.get("healthcare_monthly", 0.0)
        + scenario.get("dependent_care_monthly", 0.0)
        + scenario.get("job_search_monthly", 0.0)
    )
    one_time_total = scenario.get("one_time_expense", 0.0) + scenario.get("relocation_cost", 0.0)
    return f"""
You are RiseArc, a financial assistant powered by Nemotron-3-Nano.
Generate a concise, practical summary based on the user's profile and scenario.
Do NOT provide investment advice, stock picks, buy/sell/hold guidance, or promises of returns.
Do NOT mention investing, investments, stocks, ETFs, crypto, portfolios, mutual funds, or bonds.
Avoid language that sounds like a recommendation to invest. Focus on cash flow, runway, debt management, and risk reduction.
Keep the tone supportive and solution-focused, never alarmist.
If asked about market products, redirect to budgeting, debt, and emergency savings fundamentals.

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
- Monthly living expenses (excl. debt): {format_currency(profile['expenses_monthly'])}
- Debt payments (monthly baseline): {format_currency(profile_debt_payment)}
- Total required monthly outflow: {format_currency(total_required_outflow)}
- Savings: {format_currency(profile['savings'])}
- Total debt: {format_currency(profile['debt'])}
- Industry: {profile['industry']}
- Job stability: {job_stability_value}
- Dependents: {profile['dependents']}

Scenario:
- Months unemployed: {scenario['months_unemployed']:.0f}
- Expense cut: {scenario['expense_cut_pct']:.0f}%
- Severance: {format_currency(scenario['severance'])}
- Unemployment benefit (monthly): {format_currency(scenario.get('unemployment_benefit_monthly', 0.0))}
- Other income (monthly): {format_currency(scenario.get('other_income_monthly', 0.0))}
- New income starts (month): {scenario.get('income_start_month', 0):.0f}
- New income amount (monthly): {format_currency(scenario.get('income_start_amount', 0.0))}
- Additional debt payments (monthly): {format_currency(scenario.get('debt_payment_monthly', 0.0))}
- Healthcare / insurance (monthly): {format_currency(scenario.get('healthcare_monthly', 0.0))}
- Dependent care (monthly): {format_currency(scenario.get('dependent_care_monthly', 0.0))}
- Job search / reskilling (monthly): {format_currency(scenario.get('job_search_monthly', 0.0))}
- Other monthly expenses: {format_currency(scenario.get('extra_monthly_expenses', 0.0))}
- Total monthly add-ons: {format_currency(monthly_addons_total)}
- One-time expense: {format_currency(scenario.get('one_time_expense', 0.0))}
- Relocation / legal (one-time): {format_currency(scenario.get('relocation_cost', 0.0))}
- Total one-time costs: {format_currency(one_time_total)}

Computed Metrics:
- Runway (months): {metrics['runway_months']:.1f}
- Risk score (0-100): {metrics['risk_score']:.0f}
- Adjusted risk score (0-100): {metrics['adjusted_risk_score']:.0f}
- Debt ratio: {metrics['debt_ratio']:.2f}
- Monthly expenses after cut: {format_currency(metrics['monthly_expenses_cut'])}
- Monthly support: {format_currency(metrics.get('monthly_support', 0.0))}
- Net monthly burn: {format_currency(metrics.get('monthly_net_burn', 0.0))}
- One-time expense: {format_currency(metrics.get('one_time_expense', 0.0))}
- Estimated savings leaks (monthly): {format_currency(savings_total)}
- Timeline signals: months_until_zero={timeline_stats['months_until_zero']:.0f}, max_drawdown={format_currency(timeline_stats['max_drawdown'])}, trend_slope={format_currency(timeline_stats['trend_slope'])}

Alert Context:
{alert}
""".strip()
