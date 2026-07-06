"""Extraction agent: raw opportunity text -> structured JSON (PLAN.md §3b).

Must explicitly capture *conflicting* figures (e.g. Pink Papaya's
"3,500-4,000/day" vs "3,800/day", or France being both "not a rush" and
"not a maybe later") rather than silently picking one.
"""
from pydantic import BaseModel, Field

from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role=(
            "You are an enterprise sales analyst extracting structured facts from a raw "
            "opportunity document (an RFQ, or CRM notes and email correspondence) for a "
            "last-mile parcel delivery service."
        ),
        data=(
            "The single block of raw opportunity text provided in the user message below, "
            "under 'User-provided data'. This may be an RFQ document, CRM call notes, or email "
            "correspondence, submitted either as one of the two known challenge opportunities or "
            "as an arbitrary prospect's own pasted text via the public /analyze endpoint."
        ),
        actions=(
            "Extract every stated figure and requirement into the response schema. When the "
            "document contains multiple, differing statements about the same fact (e.g. two "
            "different daily volume numbers, or two stakeholders disagreeing on market scope), "
            "record every distinct mention with its source context in the relevant list field, "
            "and describe the conflict explicitly in `contradictions`. `daily_volume_mentions` "
            "must always be an average-per-day figure: if the document only states an annual or "
            "monthly total (never a literal 'per day' number), convert it yourself — annual total "
            "/ 365, or monthly total / ~30 — and say so in that mention's `context` (e.g. "
            "'derived: 2,920,000/year ÷ 365'). Never record an annual or monthly total directly as "
            "if it were itself a daily figure — that produces a >100x pricing and volume error "
            "downstream."
        ),
        guardrails=(
            "Never silently pick one figure or average conflicting figures — under-claiming "
            "certainty is better than smoothing over a real disagreement. Never invent a figure, "
            "requirement, or pain point that is not actually stated or clearly implied in the text. "
            "Never put an annual/monthly total into `daily_volume_mentions` without converting it "
            "to a daily basis first."
        ),
        channels=(
            "Called only by backend/agents/pipeline.py (server-side), never directly by an "
            "end user. Your structured output is consumed by downstream agents, not shown "
            "raw to the prospect."
        ),
    )
)


class FigureMention(BaseModel):
    value: float
    context: str = Field(description="who/where this figure came from, e.g. 'Lucía, call, normal week'")


class GeographyMention(BaseModel):
    region: str
    pct_of_volume: float | None = None
    context: str


class ExtractionResult(BaseModel):
    company_name: str
    daily_volume_mentions: list[FigureMention] = Field(
        description="every distinct daily-volume figure mentioned, not a single averaged number"
    )
    geography_mentions: list[GeographyMention]
    weight_and_size_profile: str = Field(
        description=(
            "Free-text summary of parcel weight/size profile. If the source document gives a "
            "weight-band % breakdown table (e.g. '0-0.5kg: 8%, 0.5-1kg: 12%, 1-2kg: 25%, ...'), "
            "reproduce those band/percentage pairs verbatim in this field rather than only a "
            "qualitative summary — a downstream agent computes a weighted-average weight from them."
        )
    )
    stated_requirements: list[str] = Field(
        description="e.g. 'weekend delivery needed', 'PUDO used as workaround', 'B2B professional-address volume'"
    )
    named_pain_points: list[str]
    contradictions: list[str] = Field(
        default_factory=list,
        description="explicit description of any conflicting figures or stakeholder disagreements found",
    )


def extract_opportunity(raw_text: str) -> ExtractionResult:
    client = get_client()
    return client.chat.completions.create(
        model=model_for("large"),
        response_model=ExtractionResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"User-provided data:\n{raw_text}"},
        ],
    )
