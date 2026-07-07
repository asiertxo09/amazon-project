"""Pitch-deck agent (PLAN.md §3b): renders a client-ready proposal as clean
Markdown (the frontend renders it) — no PPTX generation, per the scope cut
in PLAN.md §6. Large model tier — this is the most client-visible output.
"""

from pydantic import BaseModel

from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role="You are writing a client-ready proposal document in Markdown for Amazon Shipping to send to a prospect.",
        data=(
            "The full internal analysis produced upstream: executive summary, pricing scenarios, "
            "risk assessment, win-probability narrative, commercial strategy — all already "
            "vetted, structured output from earlier agents in this pipeline."
        ),
        actions=(
            "Structure the proposal with headers: title, why Amazon Shipping, recommended "
            "pricing, addressing their key concerns, next steps. Tone: confident, concise, "
            "client-facing — not an internal analyst memo."
        ),
        guardrails=(
            "Do not invent numbers not present in the supplied analysis. Unlike every other "
            "agent in this pipeline, this document may be read by the prospect themselves — omit "
            "internal-only detail such as our exact margin-floor guardrail thresholds, named "
            "comparable competitor deals, or any note that the prospect's own figures were "
            "internally flagged as contradictory; keep those in the internal Contract fields, "
            "not this client-facing document."
        ),
        channels=(
            "Called only by backend/agents/pipeline.py (server-side). Unlike the other agents, "
            "this output is the one field of the Contract (`pitch_deck_url_or_markdown`) that "
            "may ultimately be shared with the prospect via a human sales rep — treat it as "
            "external-facing, not an internal memo."
        ),
    )
)


class PitchDeckResult(BaseModel):
    markdown: str


def generate_pitch_deck(context: dict) -> PitchDeckResult:
    client = get_client()
    return client.chat.completions.create(
        model=model_for("large"),
        response_model=PitchDeckResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(context)},
        ],
    )
