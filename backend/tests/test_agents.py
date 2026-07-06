from unittest.mock import MagicMock

from backend.agents.extraction import ExtractionResult, extract_opportunity
from backend.agents.gap_feasibility import GapFeasibilityResult, assess_feasibility


def _fake_extraction_result() -> ExtractionResult:
    return ExtractionResult(
        company_name="Pink Papaya S.L.",
        daily_volume_mentions=[
            {"value": 3500, "context": "Lucía, call, normal week low end"},
            {"value": 4000, "context": "Lucía, call, normal week high end"},
            {"value": 3800, "context": "Lucía, email, normal week"},
        ],
        geography_mentions=[{"region": "Spain", "pct_of_volume": 76, "context": "Lucía email"}],
        weight_and_size_profile="mostly <2kg apparel, some heavier Papaya Home items",
        stated_requirements=["weekend delivery important"],
        named_pain_points=["peak collapse", "slow claims", "poor customer service"],
        contradictions=["Daily volume stated as 3,500-4,000/day on the call vs 3,800/day in the follow-up email"],
    )


def test_extract_opportunity_calls_llm_with_schema_and_returns_result(monkeypatch):
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = _fake_extraction_result()
    monkeypatch.setattr("backend.agents.extraction.get_client", lambda: fake_client)

    result = extract_opportunity("some raw opportunity text")

    assert isinstance(result, ExtractionResult)
    assert result.company_name == "Pink Papaya S.L."
    assert len(result.contradictions) == 1
    call_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_model"] is ExtractionResult
    assert call_kwargs["messages"][1]["content"] == "User-provided data:\nsome raw opportunity text"


def test_assess_feasibility_grounds_prompt_in_rag_passages(monkeypatch):
    fake_result = GapFeasibilityResult(
        exclusions=[{"reason": "PUDO not supported (home delivery only)", "volume_impact_pct": 0.05}],
        serviceable_daily_volume_estimate=3400,
        geo_fit_pct_estimate=0.76,
        feasibility_notes="Grounded in Service_description.pptx slide 3 and slide 6.",
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
            "defaulted_fields": ["competitive_intensity", "sales_cycle_touches", "decision_time_days"],
        },
    )
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_result
    monkeypatch.setattr("backend.agents.gap_feasibility.get_client", lambda: fake_client)

    result = assess_feasibility(_fake_extraction_result())

    assert isinstance(result, GapFeasibilityResult)
    call_kwargs = fake_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_model"] is GapFeasibilityResult
    user_message = call_kwargs["messages"][1]["content"]
    assert "Service_description.pptx" in user_message
    assert "Pink Papaya" in user_message
