"""LLM provider adapter — Groq primary, NVIDIA NIM fallback (PLAN.md §3b/3c).

Both are OpenAI-SDK compatible, so swapping providers is a config change
(`LLM_PROVIDER=groq|nvidia`), not a rewrite. `instructor` patches the client
for schema-enforced Pydantic outputs.
"""
import os
from typing import Literal

import instructor
from openai import OpenAI

ProviderName = Literal["groq", "nvidia"]
ModelTier = Literal["large", "small"]

PROVIDER_CONFIG = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1", "api_key_env": "NVIDIA_API_KEY"},
}

# Best-known model names at time of writing (PLAN.md §3d) — confirm against
# the live Groq/NVIDIA catalogs before a demo, names drift.
MODEL_TIERS = {
    "groq": {"large": "llama-3.3-70b-versatile", "small": "llama-3.1-8b-instant"},
    "nvidia": {"large": "meta/llama-3.1-70b-instruct", "small": "meta/llama-3.1-8b-instruct"},
}


class LLMNotConfiguredError(RuntimeError):
    pass


def current_provider() -> ProviderName:
    return os.environ.get("LLM_PROVIDER", "groq")  # type: ignore[return-value]


def model_for(tier: ModelTier) -> str:
    return MODEL_TIERS[current_provider()][tier]


def get_client() -> instructor.Instructor:
    provider = current_provider()
    if provider not in PROVIDER_CONFIG:
        raise LLMNotConfiguredError(f"Unknown LLM_PROVIDER '{provider}', expected 'groq' or 'nvidia'")

    config = PROVIDER_CONFIG[provider]
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        raise LLMNotConfiguredError(
            f"{config['api_key_env']} is not set — cannot call the {provider} LLM provider. "
            "Set it as an environment variable (or Render secret) before running agents that need it."
        )

    raw_client = OpenAI(api_key=api_key, base_url=config["base_url"])
    return instructor.from_openai(raw_client)
