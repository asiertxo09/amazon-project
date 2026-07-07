from backend.agents.prompt_framework import AgentPromptSpec, build_system_prompt


def test_build_system_prompt_includes_all_five_sections_and_trust_layer():
    spec = AgentPromptSpec(
        role="ROLE_MARKER",
        data="DATA_MARKER",
        actions="ACTIONS_MARKER",
        guardrails="GUARDRAILS_MARKER",
        channels="CHANNELS_MARKER",
    )
    prompt = build_system_prompt(spec)

    assert "ROLE_MARKER" in prompt
    assert "DATA_MARKER" in prompt
    assert "ACTIONS_MARKER" in prompt
    assert "GUARDRAILS_MARKER" in prompt
    assert "CHANNELS_MARKER" in prompt
    assert "TRUST & SECURITY" in prompt
    assert "DATA to analyze" in prompt

    # sections must appear in a stable order: role, data, actions, guardrails, channels, trust layer
    order = [
        prompt.index(m)
        for m in [
            "ROLE_MARKER",
            "DATA_MARKER",
            "ACTIONS_MARKER",
            "GUARDRAILS_MARKER",
            "CHANNELS_MARKER",
            "TRUST & SECURITY",
        ]
    ]
    assert order == sorted(order)


def test_all_agent_system_prompts_use_the_shared_framework():
    from backend.agents.extraction import SYSTEM_PROMPT as extraction_prompt
    from backend.agents.gap_feasibility import SYSTEM_PROMPT as gap_prompt
    from backend.agents.pitch_deck import SYSTEM_PROMPT as pitch_prompt
    from backend.agents.risk_pricing_narrative import SYSTEM_PROMPT as risk_prompt
    from backend.agents.synthesis import SYSTEM_PROMPT as synthesis_prompt
    from backend.agents.win_prob_narrative import SYSTEM_PROMPT as win_prob_prompt

    for prompt in [
        extraction_prompt,
        gap_prompt,
        pitch_prompt,
        risk_prompt,
        synthesis_prompt,
        win_prob_prompt,
    ]:
        assert "ROLE" in prompt
        assert "DATA" in prompt
        assert "ACTIONS" in prompt
        assert "GUARDRAILS" in prompt
        assert "CHANNELS" in prompt
        assert "TRUST & SECURITY" in prompt
