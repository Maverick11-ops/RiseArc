from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class Profile(BaseModel):
    income_monthly: float = Field(ge=0)
    expenses_monthly: float = Field(ge=0)
    savings: float = Field(ge=0)
    debt: float = Field(ge=0)
    industry: str = "Other"
    job_stability: Literal["stable", "medium", "unstable"] = "stable"
    dependents: int = Field(ge=0)


class Scenario(BaseModel):
    months_unemployed: int = Field(ge=0, le=36)
    expense_cut_pct: float = Field(ge=0, le=70)
    severance: float = Field(ge=0)
    unemployment_benefit_monthly: float = Field(ge=0, default=0.0)
    other_income_monthly: float = Field(ge=0, default=0.0)
    extra_monthly_expenses: float = Field(ge=0, default=0.0)
    debt_payment_monthly: float = Field(ge=0, default=0.0)
    healthcare_monthly: float = Field(ge=0, default=0.0)
    dependent_care_monthly: float = Field(ge=0, default=0.0)
    job_search_monthly: float = Field(ge=0, default=0.0)
    one_time_expense: float = Field(ge=0, default=0.0)
    relocation_cost: float = Field(ge=0, default=0.0)


class Subscription(BaseModel):
    name: str
    monthly_cost: float = Field(ge=0)


class NewsEvent(BaseModel):
    headline: str
    risk_delta: float = Field(ge=-50, le=50)
    industry: Optional[str] = None


class AnalyzeRequest(BaseModel):
    profile: Profile
    scenario: Scenario
    subscriptions: List[Subscription] = []
    news_event: Optional[NewsEvent] = None


class Metrics(BaseModel):
    monthly_expenses_cut: float
    monthly_net_burn: float
    monthly_support: float
    one_time_expense: float
    runway_months: float
    debt_ratio: float
    risk_score: float
    adjusted_risk_score: float


class AnalyzeResponse(BaseModel):
    metrics: Metrics
    timeline: List[float]
    savings_total: float
    alert: str
    summary: str
