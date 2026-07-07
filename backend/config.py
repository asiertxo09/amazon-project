"""Centralized application configuration (Plan_v2 P1-A6).

Single, typed source of truth for environment-driven settings. Import
``get_settings()`` instead of reading ``os.environ`` directly, so configuration is
declared, documented, and validated in one place.

Values come from the process environment only — we deliberately do *not*
auto-load ``.env`` here, so tests and CI stay deterministic. For local dev, pass
the file explicitly (``uvicorn backend.main:app --env-file .env``) or let
docker-compose inject the variables. Every recognized variable is documented in
``.env.example``.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    # Which LLM provider the agent layer uses ("groq" or "nvidia"). Kept as a
    # plain string (not a Literal) so an unrecognized value surfaces as our own
    # LLMNotConfiguredError at call time rather than a startup ValidationError.
    llm_provider: str = "groq"

    # Provider API keys — optional so the fixture-fallback demo path works
    # without secrets. The relevant one is required only when its provider is
    # actually called (checked in agents/llm_client.py).
    groq_api_key: str | None = None
    nvidia_api_key: str | None = None

    # Allowed CORS origins for the API. Defaults to permissive to preserve
    # current behavior; lock to the deployed frontend origin in production
    # (Plan_v2 P1-B3). Provide as a JSON array in the env var, e.g.
    # CORS_ALLOW_ORIGINS='["https://app.example.com"]'.
    cors_allow_origins: list[str] = ["*"]


def get_settings() -> Settings:
    """Build a Settings instance from the current environment.

    Not cached: constructed per call so env changes (e.g. monkeypatch in tests,
    or a re-read after config rotation) are always reflected. Construction is
    cheap relative to anything the app does with the result.
    """
    return Settings()
