"""Win-probability narrative agent (PLAN.md §3b/§3d): wraps the ML model's
output into a plain-language "why this score." Small/fast model tier — it
only narrates a number the classifier already computed, never changes it.
"""

from pydantic import BaseModel

from backend.agents.llm_client import get_client, model_for
from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt

SYSTEM_PROMPT = build_system_prompt(
    AgentPromptSpec(
        role="You are narrating the output of a trained win-probability classifier for a sales lead.",
        data=(
            "The classifier's probability output (value + top signed contributing factors) and a "
            "handful of comparable historical deals with real outcomes, both computed "
            "deterministically upstream — not free text from a prospect."
        ),
        actions=(
            "Write ONE short paragraph (3-4 sentences) in plain commercial language explaining "
            "why the score is what it is, referencing the top factors and, where useful, the "
            "comparable deals."
        ),
        guardrails="Never state a different probability than the one given — narrate it, don't recompute it.",
        channels=(
            "Called only by backend/agents/pipeline.py (server-side), small/fast model tier since "
            "it only narrates a number already computed. Feeds the synthesis agent."
        ),
    )
)


class WinProbNarrativeResult(BaseModel):
    narrative: str


def narrate_win_probability(
    win_probability: dict, comparables: list[dict]
) -> WinProbNarrativeResult:
    user_content = (
        f"Win probability output:\n{win_probability}\n\nComparable historical deals:\n{comparables}"
    )

    client = get_client()
    return client.chat.completions.create(
        model=model_for("small"),
        response_model=WinProbNarrativeResult,
        max_retries=2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
