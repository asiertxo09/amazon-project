"""Gap/feasibility agent (PLAN.md §3b): cross-checks structured requirements
against Service Description capabilities (RAG over the capability doc) ->
produces the `exclusions` list and serviceable-volume inputs.
"""
from typing import Literal

from pydantic import BaseModel, Field

from backend.agents.extraction import ExtractionResult
from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt
from backend.rag import get_store

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role=(
            "You are a feasibility analyst for Amazon Shipping, a Spain-peninsula + Balearic "
            "Islands, home-delivery-only, B2C, <=15kg/<=80x80x60cm parcel carrier."
        ),
        data=(
            "Two inputs in the user message, both labelled: (1) already-structured "
            "'Extracted opportunity data' produced by an upstream extraction agent, and (2) "
            "'Grounding passages' — short excerpts retrieved from the official Service "
            "Description and pricing guardrails documents, the only source of truth for what "
            "the service can and cannot do."
        ),
        actions=(
            "Identify every requirement the service CANNOT currently fulfil (e.g. international "
            "delivery, PUDO/locker delivery, B2B/business-address delivery, oversized parcels) "
            "and estimate the resulting serviceable volume and geo-fit. Also populate "
            "`win_model_features`: deal-context numbers used by a win-probability classifier. "
            "For avg_weight_kg specifically: if the extracted data's weight_and_size_profile "
            "describes a weight-band % distribution (e.g. '0-0.5kg: 8%, 0.5-1kg: 12%, ...'), you "
            "MUST compute the weighted average using each band's midpoint (e.g. the 2-5kg band "
            "contributes 3.5 * 0.28), not guess a low round number — this is arithmetic, not an "
            "internal BD metric, so it does not belong in `defaulted_fields`. Only fields like "
            "competitive_intensity, sales_cycle_touches, and decision_time_days are internal BD "
            "tracking metrics a prospect would never state directly — for those, give your best "
            "reasoned estimate from context and list the field name in `defaulted_fields`."
        ),
        guardrails=(
            "Cite only the grounding passages provided — never invent a capability or limit not "
            "in them. If the prospect's own figures are already in conflict (see "
            "`contradictions` in the extracted data), carry that uncertainty into the "
            "serviceable-volume estimate rather than silently resolving it. Every estimated "
            "(not directly stated) win_model_features value must be listed in `defaulted_fields`."
        ),
        channels=(
            "Called only by backend/agents/pipeline.py (server-side) after extraction. Never "
            "receives raw, unprocessed prospect text directly — only the extraction agent's "
            "already schema-validated output plus our own internal documents."
        ),
    )
)

GROUNDING_QUERIES = [
    "maximum weight and dimensions allowed",
    "geographic coverage areas served",
    "PUDO pickup drop-off locker capability",
    "B2B business delivery capability",
    "international cross-border delivery capability",
]


class ExclusionFinding(BaseModel):
    reason: str
    volume_impact_pct: float = Field(ge=0, le=1)


class WinModelFeatureEstimate(BaseModel):
    """Estimates of the win-probability model's remaining inputs (PLAN.md §3a)
    that aren't directly stated in a raw opportunity doc — e.g. a prospect
    never says 'competitive_intensity=3'. Defaulted fields must be flagged
    by the caller as assumptions, not presented as hard facts."""

    avg_weight_kg: float
    oversized_pct: float = Field(ge=0, le=1)
    requires_intl: bool
    requires_pudo: bool
    requires_b2b: bool
    weekend_need: bool
    pain_severity: int = Field(ge=1, le=5)
    price_vs_incumbent_pct: float
    competitive_intensity: int = Field(ge=1, le=5)
    sales_cycle_touches: int
    decision_time_days: int
    contract_length_months: int
    industry: str
    source: Literal["Inbound", "Outbound", "Referral", "Partner"]
    defaulted_fields: list[str] = Field(
        default_factory=list, description="names of fields above that had no textual basis and were defaulted"
    )


class GapFeasibilityResult(BaseModel):
    exclusions: list[ExclusionFinding]
    serviceable_daily_volume_estimate: float
    geo_fit_pct_estimate: float = Field(ge=0, le=1)
    feasibility_notes: str
    win_model_features: WinModelFeatureEstimate


def _gather_grounding_passages() -> list[dict]:
    store = get_store()
    seen: dict[str, dict] = {}
    for query in GROUNDING_QUERIES:
        for passage in store.search(query, k=3):
            key = f"{passage['doc']}::{passage['detail']}::{passage['text']}"
            seen[key] = passage
    return list(seen.values())


def assess_feasibility(extraction: ExtractionResult) -> GapFeasibilityResult:
    passages = _gather_grounding_passages()
    grounding_text = "\n".join(f"- [{p['doc']} / {p['detail']}] {p['text']}" for p in passages)

    user_content = (
        f"Extracted opportunity data:\n{extraction.model_dump_json(indent=2)}\n\n"
        f"Grounding passages (Service Description + pricing guardrails):\n{grounding_text}"
    )

    client = get_client()
    return client.chat.completions.create(
        model=model_for("large"),
        response_model=GapFeasibilityResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
