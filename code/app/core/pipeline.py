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
    runway_months = compute_runway(profile.savings, monthly_expenses_cut, scenario.severance)
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

    timeline = build_timeline(profile.savings, monthly_expenses_cut, scenario.months_unemployed, scenario.severance)
    timeline_stats = compute_timeline_stats(timeline)

    savings_total = total_savings_leaks([s.monthly_cost for s in payload.subscriptions])

    metrics: Dict[str, float] = {
        "monthly_expenses_cut": monthly_expenses_cut,
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
