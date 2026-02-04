from typing import Dict

from .models import AnalyzeRequest, AnalyzeResponse, Metrics
from .prompts import build_summary_prompt
from .tools import (
    build_timeline,
    clamp_llm_metrics,
    clamp_llm_profile,
    clamp_llm_scenario,
    clamp_llm_savings_total,
    clamp_llm_timeline_stats,
    compute_timeline_stats,
    compute_debt_ratio,
    compute_risk_score,
    compute_runway,
    job_stability_label,
    job_stability_weight,
    total_savings_leaks,
    clamp,
)
from app.ai.nemotron_client import extract_text, query_nemotron


def run_analysis(payload: AnalyzeRequest) -> AnalyzeResponse:
    profile = payload.profile
    scenario = payload.scenario

    monthly_expenses_cut = profile.expenses_monthly * (1 - scenario.expense_cut_pct / 100.0)
    monthly_support = scenario.unemployment_benefit_monthly + scenario.other_income_monthly
    monthly_addons = (
        scenario.extra_monthly_expenses
        + scenario.debt_payment_monthly
        + scenario.healthcare_monthly
        + scenario.dependent_care_monthly
        + scenario.job_search_monthly
    )
    monthly_net_burn = monthly_expenses_cut + monthly_addons - monthly_support
    one_time_total = scenario.one_time_expense + scenario.relocation_cost
    starting_balance = profile.savings + scenario.severance - one_time_total
    if monthly_net_burn <= 0:
        runway_months = 60.0
    else:
        runway_months = compute_runway(max(starting_balance, 0.0), monthly_net_burn, 0.0)
    debt_ratio = compute_debt_ratio(profile.debt, profile.income_monthly)
    risk_score = compute_risk_score(runway_months, debt_ratio, profile.job_stability, profile.industry)

    adjusted_risk = risk_score
    alert = "No alerts yet."
    if payload.news_event:
        event = payload.news_event
        delta = event.risk_delta
        if event.industry and event.industry != profile.industry:
            delta *= 0.5
        adjusted_risk = clamp(risk_score + delta, 0.0, 100.0)
        alert = f"Headline: {event.headline} | Risk adjusted by {delta:+.0f} to {adjusted_risk:.0f}."

    timeline = build_timeline(starting_balance, max(monthly_net_burn, 0.0), scenario.months_unemployed, 0.0)
    timeline_stats = compute_timeline_stats(timeline)

    savings_total = total_savings_leaks([s.monthly_cost for s in payload.subscriptions])

    metrics: Dict[str, float] = {
        "monthly_expenses_cut": monthly_expenses_cut,
        "monthly_net_burn": monthly_net_burn,
        "monthly_support": monthly_support,
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
            "extra_monthly_expenses": scenario.extra_monthly_expenses,
            "debt_payment_monthly": scenario.debt_payment_monthly,
            "healthcare_monthly": scenario.healthcare_monthly,
            "dependent_care_monthly": scenario.dependent_care_monthly,
            "job_search_monthly": scenario.job_search_monthly,
            "one_time_expense": scenario.one_time_expense,
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
    response = query_nemotron(prompt)
    summary = extract_text(response)

    return AnalyzeResponse(
        metrics=Metrics(**metrics),
        timeline=timeline,
        savings_total=savings_total,
        alert=alert,
        summary=summary,
    )
