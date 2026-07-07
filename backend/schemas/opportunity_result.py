"""The Contract — single shared shape returned by POST /analyze.

Mirrored in frontend/fixtures/example_result.json. Keep field names stable;
extend only if a phase genuinely needs a new field (see PLAN.md §2).
"""

from typing import Literal

from pydantic import BaseModel, Field


class OpportunityScore(BaseModel):
    value: int = Field(ge=0, le=100)
    label: Literal["Strong", "Moderate", "Weak"]
    rationale: str


class Exclusion(BaseModel):
    reason: str
    volume_impact_pct: float


class ServiceableVolume(BaseModel):
    declared_daily_volume: float
    serviceable_daily_volume: float
    geo_fit_pct: float
    exclusions: list[Exclusion] = Field(default_factory=list)


class RiskItem(BaseModel):
    category: Literal["Operational", "Commercial", "Financial"]
    risk: str
    severity: Literal["Low", "Med", "High"]
    evidence: str


class PricingScenario(BaseModel):
    name: Literal["Aggressive", "Balanced", "Conservative"]
    margin_pct: float
    avg_price_per_parcel_eur: float
    rationale: str
    tradeoffs: str


class TopFactor(BaseModel):
    factor: str
    direction: Literal["+", "-"]


class WinProbability(BaseModel):
    value_pct: int = Field(ge=0, le=100)
    model: str
    top_factors: list[TopFactor] = Field(default_factory=list)


class Source(BaseModel):
    doc: str
    detail: str


class OpportunityResult(BaseModel):
    opportunity_id: str
    company_name: str
    executive_summary: str
    opportunity_score: OpportunityScore
    serviceable_volume: ServiceableVolume
    risk_assessment: list[RiskItem]
    pricing_scenarios: list[PricingScenario]
    commercial_strategy: str
    follow_up_actions: list[str]
    win_probability: WinProbability
    pitch_deck_url_or_markdown: str
    sources_used: list[Source]
    assumptions_and_open_questions: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    demo: Literal["tecnomania", "pink_papaya"] | None = None
    opportunity_text: str | None = None
    company_name: str | None = None
