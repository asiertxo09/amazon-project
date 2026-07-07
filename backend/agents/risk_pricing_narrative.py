"""Risk + pricing narrative agent (PLAN.md §3b): wraps the deterministic
pricing engine + guardrail output into a risk assessment and per-scenario
rationale/tradeoffs. Numeric fields (margin_pct, price) are already computed
by backend/pricing.py — this agent only narrates them; it never invents or
overrides a number.
"""

from typing import Literal

from pydantic import BaseModel

from backend.agents.extraction import ExtractionResult
from backend.agents.gap_feasibility import GapFeasibilityResult
from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role="You are a commercial risk analyst for Amazon Shipping.",
        data=(
            "Three inputs in the user message: extracted prospect data (from the extraction "
            "agent), a feasibility assessment (from the gap/feasibility agent), and deterministic "
            "pricing scenarios already computed by backend/pricing.py — the numeric fields in "
            "those scenarios are ground truth, not suggestions."
        ),
        actions=(
            "Write (1) a risk assessment: 2-4 risks across Operational/Commercial/Financial "
            "categories, each with a severity and the evidence it's grounded in; and (2) for each "
            "of the three pricing scenarios provided, a one-sentence rationale and a one-sentence "
            "tradeoff in commercial language a sales lead could read to a client."
        ),
        guardrails=(
            "Never change or invent the numeric fields (margin_pct, avg_price_per_parcel_eur) — "
            "narrate them, don't alter them. The scenario `name` in your output MUST exactly match "
            'one of "Aggressive", "Balanced", "Conservative", copied verbatim from the input. '
            "Ground every risk in something actually stated in the extracted data or feasibility "
            "notes — do not invent risks with no evidentiary basis. If the prospect's own figures "
            "were in conflict, that conflict itself is a valid Operational or Commercial risk."
        ),
        channels=(
            "Called only by backend/agents/pipeline.py (server-side), downstream of extraction "
            "and feasibility. Output feeds the synthesis and pitch-deck agents, not the prospect "
            "directly."
        ),
    )
)


class RiskItem(BaseModel):
    category: Literal["Operational", "Commercial", "Financial"]
    risk: str
    severity: Literal["Low", "Med", "High"]
    evidence: str


class ScenarioNarrative(BaseModel):
    name: Literal["Aggressive", "Balanced", "Conservative"]
    rationale: str
    tradeoffs: str


class RiskPricingNarrativeResult(BaseModel):
    risk_assessment: list[RiskItem]
    scenario_narratives: list[ScenarioNarrative]


def narrate_risk_and_pricing(
    extraction: ExtractionResult,
    feasibility: GapFeasibilityResult,
    pricing_scenarios: list[dict],
) -> RiskPricingNarrativeResult:
    user_content = (
        f"Extracted data:\n{extraction.model_dump_json(indent=2)}\n\n"
        f"Feasibility assessment:\n{feasibility.model_dump_json(indent=2)}\n\n"
        f"Deterministic pricing scenarios (do not alter these numbers):\n{pricing_scenarios}"
    )

    client = get_client()
    return client.chat.completions.create(
        model=model_for("large"),
        response_model=RiskPricingNarrativeResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
