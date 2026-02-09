from typing import Dict, List

from .models import AnalyzeRequest, AnalyzeResponse, Metrics
from .prompts import build_summary_prompt
from .tools import (
    clamp_llm_metrics,
    clamp_llm_profile,
    clamp_llm_scenario,
    clamp_llm_savings_total,
    clamp_llm_timeline_stats,
    compute_timeline_stats,
    compute_debt_ratio,
    compute_risk_score,
    adjust_risk_for_scenario,
    job_stability_label,
    job_stability_weight,
    total_savings_leaks,
    clamp,
)
from app.ai.nemotron_client import extract_text, query_nemotron


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _deterministic_summary(payload: AnalyzeRequest, metrics: Dict[str, float], timeline_stats: Dict[str, float], alert: str) -> str:
    profile = payload.profile
    scenario = payload.scenario
    monthly_net_burn = float(metrics.get("monthly_net_burn", 0.0))
    runway_months = float(metrics.get("runway_months", 0.0))
    risk_score = float(metrics.get("adjusted_risk_score", metrics.get("risk_score", 0.0)))
    debt_ratio = float(metrics.get("debt_ratio", 0.0))

    if monthly_net_burn > 0:
        summary_line = (
            f"- Net burn is {_money(monthly_net_burn)}/mo, so savings last about {runway_months:.1f} months in this scenario."
        )
        warning_line = f"- At this burn rate, cash may reach zero around month {timeline_stats.get('months_until_zero', runway_months):.0f}."
    elif monthly_net_burn < 0:
        summary_line = f"- Scenario cash flow is positive by {_money(abs(monthly_net_burn))}/mo, so savings are growing."
        warning_line = "- If support drops or expenses rise, the surplus can disappear quickly."
    else:
        summary_line = "- Scenario cash flow is roughly break-even, so savings stay flat unless assumptions change."
        warning_line = "- Small changes in costs or support can push this scenario into deficit."

    phase_line = ""
    if scenario.income_start_month > 0 and scenario.income_start_amount > 0:
        phase_line = (
            f"- Additional income of {_money(scenario.income_start_amount)}/mo starts in month {scenario.income_start_month}, "
            "improving cash flow after that point."
        )

    lines: List[str] = [
        "Summary:",
        summary_line,
        f"- Debt ratio is {debt_ratio:.2f} ({debt_ratio * 100:.0f}% of annual income) and adjusted risk is {risk_score:.0f}/100.",
    ]
    if phase_line:
        lines.append(phase_line)

    lines.extend(
        [
            "",
            "Actions:",
            "- Stabilize income first and protect a cash buffer before taking new obligations.",
            "- Reduce discretionary spending to lower monthly burn.",
            "- Prioritize high-interest debt payments once near-term cash risk is controlled.",
            "",
            "Warnings:",
            warning_line,
        ]
    )
    if alert and alert != "No alerts yet.":
        lines.append(f"- {alert}")
    if profile.dependents > 0:
        lines.append("- Dependent costs increase downside risk if unemployment lasts longer than expected.")

    return "\n".join(lines).strip()


def run_analysis(payload: AnalyzeRequest) -> AnalyzeResponse:
    profile = payload.profile
    scenario = payload.scenario

    profile_debt_payment = float(getattr(profile, "debt_payment_monthly", 0.0))
    monthly_expenses_cut = profile.expenses_monthly * (1 - scenario.expense_cut_pct / 100.0) + profile_debt_payment
    monthly_support_base = (
        scenario.unemployment_benefit_monthly
        + scenario.other_income_monthly
        + scenario.income_change_monthly
    )
    # Keep support non-negative for display/LLM consistency while preserving net burn.
    # Any net-negative support is treated as an additional monthly cost.
    support_shortfall = max(-monthly_support_base, 0.0)
    monthly_support = max(monthly_support_base, 0.0)
    monthly_addons = (
        scenario.extra_monthly_expenses
        + scenario.debt_payment_monthly
        + scenario.healthcare_monthly
        + scenario.dependent_care_monthly
        + scenario.job_search_monthly
        + support_shortfall
    )
    income_start_month = scenario.income_start_month
    income_start_amount = scenario.income_start_amount

    def support_for_month(month: int) -> float:
        support = monthly_support
        if income_start_month > 0 and income_start_amount > 0 and month >= income_start_month:
            support += income_start_amount
        return support

    def net_burn_for_month(month: int) -> float:
        return monthly_expenses_cut + monthly_addons - support_for_month(month)

    monthly_support_first_month = support_for_month(1)
    monthly_net_burn = net_burn_for_month(1)
    one_time_total = scenario.one_time_expense + scenario.relocation_cost
    starting_balance = profile.savings + scenario.severance + scenario.one_time_income - one_time_total

    max_months = 60
    if starting_balance <= 0:
        runway_months = 0.0
    else:
        runway_months = float(max_months)
        balance_probe = starting_balance
        for month in range(1, max_months + 1):
            balance_probe -= net_burn_for_month(month)
            if balance_probe <= 0:
                runway_months = float(month)
                break

    debt_ratio = compute_debt_ratio(profile.debt, profile.income_monthly)
    base_risk = compute_risk_score(runway_months, debt_ratio, profile.job_stability, profile.industry)
    risk_score = adjust_risk_for_scenario(base_risk, runway_months, scenario.months_unemployed)

    adjusted_risk = risk_score
    alert = "No alerts yet."
    if payload.news_event:
        event = payload.news_event
        delta = event.risk_delta
        if event.industry and event.industry != profile.industry:
            delta *= 0.5
        adjusted_risk = clamp(risk_score + delta, 0.0, 100.0)
        alert = f"Headline: {event.headline} | Risk adjusted by {delta:+.0f} to {adjusted_risk:.0f}."

    horizon = max(scenario.months_unemployed, 1, scenario.income_start_month, 36)
    timeline: List[float] = []
    balance = starting_balance
    for month in range(0, horizon + 1):
        if month == 0:
            timeline.append(round(balance, 2))
            continue
        balance -= net_burn_for_month(month)
        timeline.append(round(balance, 2))
    timeline_stats = compute_timeline_stats(timeline)

    savings_total = total_savings_leaks([s.monthly_cost for s in payload.subscriptions])

    metrics: Dict[str, float] = {
        "monthly_expenses_cut": monthly_expenses_cut,
        "monthly_net_burn": monthly_net_burn,
        "monthly_support": monthly_support_first_month,
        "one_time_expense": one_time_total,
        "runway_months": runway_months,
        "debt_ratio": debt_ratio,
        "risk_score": risk_score,
        "adjusted_risk_score": adjusted_risk,
    }

    llm_metrics = clamp_llm_metrics(metrics)
    llm_profile = clamp_llm_profile(
        {
            "income_monthly": profile.income_monthly,
            "expenses_monthly": profile.expenses_monthly,
            "debt_payment_monthly": profile_debt_payment,
            "savings": profile.savings,
            "debt": profile.debt,
            "industry": profile.industry,
            "job_stability": profile.job_stability,
            "dependents": profile.dependents,
        }
    )
    llm_scenario = clamp_llm_scenario(
        {
            "months_unemployed": scenario.months_unemployed,
            "expense_cut_pct": scenario.expense_cut_pct,
            "severance": scenario.severance,
            "unemployment_benefit_monthly": scenario.unemployment_benefit_monthly,
            "other_income_monthly": scenario.other_income_monthly,
            "income_start_month": scenario.income_start_month,
            "income_start_amount": scenario.income_start_amount,
            "income_change_monthly": scenario.income_change_monthly,
            "extra_monthly_expenses": scenario.extra_monthly_expenses,
            "debt_payment_monthly": scenario.debt_payment_monthly,
            "healthcare_monthly": scenario.healthcare_monthly,
            "dependent_care_monthly": scenario.dependent_care_monthly,
            "job_search_monthly": scenario.job_search_monthly,
            "one_time_expense": scenario.one_time_expense,
            "one_time_income": scenario.one_time_income,
            "relocation_cost": scenario.relocation_cost,
        }
    )
    llm_timeline_stats = clamp_llm_timeline_stats(timeline_stats)
    llm_savings_total = clamp_llm_savings_total(savings_total)
    stability_label = job_stability_label(profile.job_stability)
    stability_weight = job_stability_weight(profile.job_stability)

    prompt = build_summary_prompt(
        llm_profile,
        llm_scenario,
        llm_metrics,
        alert,
        llm_savings_total,
        llm_timeline_stats,
        stability_label,
        stability_weight,
    )
    summary = ""
    try:
        response = query_nemotron(prompt)
        summary = extract_text(response).strip()
    except Exception:
        summary = ""

    if not summary:
        summary = _deterministic_summary(payload, metrics, timeline_stats, alert)

    return AnalyzeResponse(
        metrics=Metrics(**metrics),
        timeline=timeline,
        savings_total=savings_total,
        alert=alert,
        summary=summary,
    )
