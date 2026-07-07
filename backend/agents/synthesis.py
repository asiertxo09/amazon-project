"""Synthesis agent (PLAN.md §3b): executive summary, opportunity score,
commercial strategy, follow-up actions, assumptions/open questions. This is
the final narrative layer over everything computed so far — it must not
invent numbers already produced deterministically (pricing, win probability).
"""

from typing import Literal

from pydantic import BaseModel, Field

from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role=(
            "You are a senior enterprise sales strategist synthesizing a complete opportunity "
            "analysis into a client-facing summary for Amazon Shipping."
        ),
        data=(
            "Extracted prospect data (including any contradictions), a feasibility assessment, "
            "risk assessment, pricing scenario narratives, and win-probability output with "
            "narrative — all already produced by upstream agents in this pipeline, not raw "
            "prospect text."
        ),
        actions=(
            "Produce: executive_summary (3-5 sentences); opportunity_score (0-100 value, a "
            "Strong/Moderate/Weak label, one-sentence rationale); commercial_strategy (a short "
            "paragraph recommending which pricing scenario to lead with and why, and how to "
            "sequence the relationship); follow_up_actions (2-4 concrete next steps for a BD rep); "
            "assumptions_and_open_questions."
        ),
        guardrails=(
            "Do not restate a different win-probability percentage or margin number than what "
            "you were given — use them as-is. Every defaulted/estimated field and every "
            "unresolved contradiction from the upstream data MUST appear in "
            "assumptions_and_open_questions — do not silently drop them. This is the one place "
            "ambiguity is guaranteed visible to the reader."
        ),
        channels=(
            "Called only by backend/agents/pipeline.py (server-side). Your output populates the "
            "top-level fields of the Contract returned by POST /analyze, read by internal Amazon "
            "Shipping staff (BD reps), not the prospect."
        ),
    )
)


class OpportunityScoreOut(BaseModel):
    value: int = Field(ge=0, le=100)
    label: Literal["Strong", "Moderate", "Weak"]
    rationale: str


class SynthesisResult(BaseModel):
    executive_summary: str
    opportunity_score: OpportunityScoreOut
    commercial_strategy: str
    follow_up_actions: list[str]
    assumptions_and_open_questions: list[str]


def synthesize(context: dict) -> SynthesisResult:
    client = get_client()
    return client.chat.completions.create(
        model=model_for("large"),
        response_model=SynthesisResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": str(context)},
        ],
    )
