"""Orchestration (PLAN.md §3c): one run_pipeline() calling each agent in
sequence; independent steps run concurrently via asyncio.gather. No
orchestration framework (explicitly not LangChain) — fully debuggable.
"""

import asyncio
import json
import uuid
from pathlib import Path

from backend.agents.extraction import ExtractionResult, extract_opportunity
from backend.agents.gap_feasibility import GapFeasibilityResult, assess_feasibility
from backend.agents.pitch_deck import generate_pitch_deck
from backend.agents.risk_pricing_narrative import narrate_risk_and_pricing
from backend.agents.synthesis import synthesize
from backend.agents.win_prob_narrative import narrate_win_probability
from backend.ml import win_model
from backend.ml.comparables import find_comparables
from backend.pricing import Region, unit_cost_eur
from backend.pricing import pricing_scenarios as compute_pricing_scenarios
from backend.schemas.opportunity_result import (
    Exclusion,
    OpportunityResult,
    OpportunityScore,
    PricingScenario,
    RiskItem,
    ServiceableVolume,
    Source,
    TopFactor,
    WinProbability,
)


def _win_model_features_dict(
    feasibility: GapFeasibilityResult, serviceable_daily_volume: float
) -> dict:
    f = feasibility.win_model_features
    return {
        "geo_fit_pct": feasibility.geo_fit_pct_estimate,
        "daily_volume_serviceable": serviceable_daily_volume,
        "avg_weight_kg": f.avg_weight_kg,
        "oversized_pct": f.oversized_pct,
        "requires_intl": int(f.requires_intl),
        "requires_pudo": int(f.requires_pudo),
        "requires_b2b": int(f.requires_b2b),
        "weekend_need": int(f.weekend_need),
        "pain_severity": f.pain_severity,
        "price_vs_incumbent_pct": f.price_vs_incumbent_pct,
        "competitive_intensity": f.competitive_intensity,
        "sales_cycle_touches": f.sales_cycle_touches,
        "decision_time_days": f.decision_time_days,
        "contract_length_months": f.contract_length_months,
        "industry": f.industry,
        "source": f.source,
    }


async def run_pipeline(
    opportunity_text: str, opportunity_id: str | None = None
) -> OpportunityResult:
    extraction: ExtractionResult = await asyncio.to_thread(extract_opportunity, opportunity_text)
    feasibility: GapFeasibilityResult = await asyncio.to_thread(assess_feasibility, extraction)

    # Deterministic sanity checks (PLAN.md §3a).
    # 1. The extraction agent is instructed to convert annual/monthly totals to a
    #    daily figure itself, but as defense-in-depth: no single opportunity in the
    #    360-row historical training set exceeds ~14,000 parcels/day (see
    #    backend/data/historical_opportunities.csv), so anything wildly above that
    #    is almost certainly an unconverted annual/monthly total slipping through —
    #    apply the same /365 conversion deterministically rather than trust it.
    PLAUSIBLE_MAX_DAILY_VOLUME = 50_000
    declared_max_volume = max((m.value for m in extraction.daily_volume_mentions), default=0)
    if declared_max_volume > PLAUSIBLE_MAX_DAILY_VOLUME:
        declared_max_volume = declared_max_volume / 365

    # 2. Serviceable volume can never exceed what the prospect actually declared,
    #    regardless of what the LLM's feasibility estimate says.
    serviceable_daily_volume = feasibility.serviceable_daily_volume_estimate
    if serviceable_daily_volume > PLAUSIBLE_MAX_DAILY_VOLUME:
        serviceable_daily_volume = serviceable_daily_volume / 365
    if declared_max_volume and serviceable_daily_volume > declared_max_volume:
        serviceable_daily_volume = declared_max_volume

    features = _win_model_features_dict(feasibility, serviceable_daily_volume)
    region: Region = (
        "balearic_islands"
        if any("balear" in g.region.lower() for g in extraction.geography_mentions)
        and not any(
            "spain" in g.region.lower() or "peninsula" in g.region.lower()
            for g in extraction.geography_mentions
        )
        else "peninsula"
    )

    unit_cost = unit_cost_eur(
        daily_volume=serviceable_daily_volume,
        weight_kg=features["avg_weight_kg"],
        region=region,
    )
    scenarios = compute_pricing_scenarios(unit_cost)

    win_prob_raw, comparables = await asyncio.gather(
        asyncio.to_thread(win_model.predict, features),
        asyncio.to_thread(find_comparables, features),
    )

    risk_pricing, win_prob_narrative = await asyncio.gather(
        asyncio.to_thread(narrate_risk_and_pricing, extraction, feasibility, scenarios),
        asyncio.to_thread(narrate_win_probability, win_prob_raw, comparables),
    )

    synthesis_context = {
        "extraction": extraction.model_dump(),
        "feasibility": feasibility.model_dump(),
        "risk_assessment": [r.model_dump() for r in risk_pricing.risk_assessment],
        "pricing_scenarios": scenarios,
        "scenario_narratives": [s.model_dump() for s in risk_pricing.scenario_narratives],
        "win_probability": win_prob_raw,
        "win_probability_narrative": win_prob_narrative.narrative,
    }

    synthesis_result, pitch_deck_result = await asyncio.gather(
        asyncio.to_thread(synthesize, synthesis_context),
        asyncio.to_thread(generate_pitch_deck, synthesis_context),
    )

    scenario_by_name = {n.name: n for n in risk_pricing.scenario_narratives}
    pricing_scenario_models = [
        PricingScenario(
            name=s["name"],
            margin_pct=s["margin_pct"],
            avg_price_per_parcel_eur=s["avg_price_per_parcel_eur"],
            rationale=scenario_by_name[s["name"]].rationale
            if s["name"] in scenario_by_name
            else "",
            tradeoffs=scenario_by_name[s["name"]].tradeoffs
            if s["name"] in scenario_by_name
            else "",
        )
        for s in scenarios
    ]

    sources_used = [
        Source(
            doc="Service_description.pptx",
            detail="capability/coverage grounding for feasibility check",
        ),
        Source(doc="PL_Industry_Challenge.xlsx", detail="pricing tables and guardrails"),
        Source(
            doc="Historical_Opportunities.xlsx",
            detail="360-row training set and comparable-deal lookup",
        ),
    ]
    market_intel_path = Path(__file__).resolve().parent.parent / "data" / "market_intelligence.json"
    for entry in json.loads(market_intel_path.read_text(encoding="utf-8"))[:2]:
        sources_used.append(Source(doc=entry["source"], detail=f"{entry['stat']} ({entry['url']})"))

    assumptions = list(synthesis_result.assumptions_and_open_questions)
    if feasibility.win_model_features.defaulted_fields:
        assumptions.append(
            "Estimated (not directly stated) deal-context fields for the win-probability model: "
            + ", ".join(feasibility.win_model_features.defaulted_fields)
        )

    return OpportunityResult(
        opportunity_id=opportunity_id or f"OPP-{uuid.uuid4().hex[:8].upper()}",
        company_name=extraction.company_name,
        executive_summary=synthesis_result.executive_summary,
        opportunity_score=OpportunityScore(**synthesis_result.opportunity_score.model_dump()),
        serviceable_volume=ServiceableVolume(
            declared_daily_volume=declared_max_volume,
            serviceable_daily_volume=serviceable_daily_volume,
            geo_fit_pct=feasibility.geo_fit_pct_estimate,
            exclusions=[
                Exclusion(reason=e.reason, volume_impact_pct=e.volume_impact_pct)
                for e in feasibility.exclusions
            ],
        ),
        risk_assessment=[RiskItem(**r.model_dump()) for r in risk_pricing.risk_assessment],
        pricing_scenarios=pricing_scenario_models,
        commercial_strategy=synthesis_result.commercial_strategy,
        follow_up_actions=synthesis_result.follow_up_actions,
        win_probability=WinProbability(
            value_pct=win_prob_raw["value_pct"],
            model=win_prob_raw["model"],
            top_factors=[TopFactor(**tf) for tf in win_prob_raw["top_factors"]],
        ),
        pitch_deck_url_or_markdown=pitch_deck_result.markdown,
        sources_used=sources_used,
        assumptions_and_open_questions=assumptions,
    )
