import pytest

from backend.agents import llm_client


def test_get_client_raises_clear_error_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    with pytest.raises(llm_client.LLMNotConfiguredError, match="GROQ_API_KEY"):
        llm_client.get_client()


def test_get_client_raises_on_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not_a_real_provider")
    with pytest.raises(llm_client.LLMNotConfiguredError, match="Unknown LLM_PROVIDER"):
        llm_client.get_client()


def test_model_for_switches_with_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert llm_client.model_for("large") == "llama-3.3-70b-versatile"
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    assert llm_client.model_for("large") == "meta/llama-3.1-70b-instruct"
