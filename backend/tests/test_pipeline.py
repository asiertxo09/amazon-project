from unittest.mock import MagicMock

import pytest

from backend.agents import pipeline
from backend.agents.extraction import ExtractionResult
from backend.agents.gap_feasibility import GapFeasibilityResult
from backend.agents.risk_pricing_narrative import RiskPricingNarrativeResult
from backend.agents.synthesis import SynthesisResult
from backend.agents.win_prob_narrative import WinProbNarrativeResult
from backend.schemas.opportunity_result import OpportunityResult


def _extraction() -> ExtractionResult:
    return ExtractionResult(
        company_name="Pink Papaya S.L.",
        daily_volume_mentions=[
            {"value": 3500, "context": "call low end"},
            {"value": 4000, "context": "call high end"},
            {"value": 3800, "context": "email"},
        ],
        geography_mentions=[{"region": "Spain", "pct_of_volume": 76, "context": "email"}],
        weight_and_size_profile="mostly <2kg apparel, some heavier home items",
        stated_requirements=["weekend delivery important"],
        named_pain_points=["peak collapse", "slow claims"],
        contradictions=["daily volume conflict between call and email"],
    )


def _feasibility() -> GapFeasibilityResult:
    return GapFeasibilityResult(
        exclusions=[{"reason": "PUDO not supported", "volume_impact_pct": 0.05}],
        serviceable_daily_volume_estimate=3400,
        geo_fit_pct_estimate=0.76,
        feasibility_notes="grounded in slide 3/6",
        win_model_features={
            "avg_weight_kg": 1.8,
            "oversized_pct": 0.03,
            "requires_intl": True,
            "requires_pudo": True,
            "requires_b2b": False,
            "weekend_need": True,
            "pain_severity": 5,
            "price_vs_incumbent_pct": 8.0,
            "competitive_intensity": 3,
            "sales_cycle_touches": 4,
            "decision_time_days": 21,
            "contract_length_months": 24,
            "industry": "Fashion & Apparel",
            "source": "Inbound",
            "defaulted_fields": ["competitive_intensity", "sales_cycle_touches"],
        },
    )


def _risk_pricing() -> RiskPricingNarrativeResult:
    return RiskPricingNarrativeResult(
        risk_assessment=[
            {"category": "Commercial", "risk": "conflicting volume figures", "severity": "Med", "evidence": "call vs email"}
        ],
        scenario_narratives=[
            {"name": "Aggressive", "rationale": "wins volume", "tradeoffs": "thin buffer"},
            {"name": "Balanced", "rationale": "midpoint", "tradeoffs": "moderate"},
            {"name": "Conservative", "rationale": "target margin", "tradeoffs": "less competitive"},
        ],
    )


@pytest.mark.asyncio
async def test_run_pipeline_assembles_valid_contract(monkeypatch):
    monkeypatch.setattr(pipeline, "extract_opportunity", lambda text: _extraction())
    monkeypatch.setattr(pipeline, "assess_feasibility", lambda extraction: _feasibility())
    monkeypatch.setattr(pipeline, "narrate_risk_and_pricing", lambda e, f, s: _risk_pricing())
    monkeypatch.setattr(
        pipeline, "narrate_win_probability", lambda wp, comps: WinProbNarrativeResult(narrative="Solid fit given geo_fit.")
    )
    monkeypatch.setattr(
        pipeline,
        "synthesize",
        lambda ctx: SynthesisResult(
            executive_summary="Summary.",
            opportunity_score={"value": 65, "label": "Moderate", "rationale": "mixed signals"},
            commercial_strategy="Lead with Balanced.",
            follow_up_actions=["Confirm real volume with client"],
            assumptions_and_open_questions=["Volume figure unresolved between call and email"],
        ),
    )
    monkeypatch.setattr(pipeline, "generate_pitch_deck", lambda ctx: MagicMock(markdown="# Proposal"))

    result = await pipeline.run_pipeline("raw opportunity text", opportunity_id="TEST-001")

    assert isinstance(result, OpportunityResult)
    assert result.opportunity_id == "TEST-001"
    assert result.company_name == "Pink Papaya S.L."
    assert len(result.pricing_scenarios) == 3
    for s in result.pricing_scenarios:
        assert s.margin_pct >= 13.0
    assert result.win_probability.model == "logreg_v1"
    assert any("competitive_intensity" in a for a in result.assumptions_and_open_questions)
