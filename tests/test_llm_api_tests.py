import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ecommerce_agent.config import (
    DEFAULT_EMBEDDING_MODELS,
    GEMINI_OPENAI_BASE_URL,
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    _DEFAULT_CHAT_MODELS,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "llm-api-tests"))

from providers import (  # noqa: E402
    CHAT_PROVIDERS,
    EMBED_PROVIDERS,
    base_url_for,
    chat_client,
    embed_client,
    embed_model_for,
    model_for,
    ping_chat,
    ping_embed,
    skip_if_unconfigured,
)


def test_chat_providers_cover_each_llm_backend():
    assert CHAT_PROVIDERS == ("openai", "openrouter", "mistral", "ollama")


def test_embed_providers_cover_remote_embedding_apis():
    assert EMBED_PROVIDERS == ("openai", "gemini")


def test_base_url_for_matches_config_constants():
    assert base_url_for("openai") == OPENAI_BASE_URL
    assert base_url_for("openrouter") == OPENROUTER_BASE_URL
    assert base_url_for("mistral") == MISTRAL_BASE_URL
    assert base_url_for("ollama") == OLLAMA_BASE_URL
    assert base_url_for("gemini") == GEMINI_OPENAI_BASE_URL


def test_model_for_uses_provider_default_not_global_model(monkeypatch):
    monkeypatch.setenv("MODEL", "should-not-win")
    monkeypatch.delenv("MISTRAL_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert model_for("mistral") == _DEFAULT_CHAT_MODELS["mistral"]
    assert model_for("openai") == _DEFAULT_CHAT_MODELS["openai"]


def test_chat_client_uses_provider_key_and_url(monkeypatch):
    import providers as mod

    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-live")
    monkeypatch.setattr(mod, "OpenAI", fake_openai)

    chat_client("mistral")

    assert captured["api_key"] == "mistral-live"
    assert captured["base_url"] == MISTRAL_BASE_URL


def test_ping_chat_sends_short_prompt():
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="pong"))]
        )

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )

    text = ping_chat(client, "mistral-small")

    assert text == "pong"
    assert captured["model"] == "mistral-small"
    assert captured["messages"][0]["content"]


def test_skip_if_unconfigured_skips_without_key(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    with pytest.raises(pytest.skip.Exception, match="MISTRAL_API_KEY"):
        skip_if_unconfigured("mistral")


def test_embed_client_uses_gemini_base_url(monkeypatch):
    import providers as mod

    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-live")
    monkeypatch.setattr(mod, "OpenAI", fake_openai)

    embed_client("gemini")

    assert captured["api_key"] == "gemini-live"
    assert captured["base_url"] == GEMINI_OPENAI_BASE_URL
    assert embed_model_for("gemini") == DEFAULT_EMBEDDING_MODELS["gemini"]


def test_ping_embed_returns_vector_length():
    def fake_create(**kwargs):
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
        )

    client = SimpleNamespace(embeddings=SimpleNamespace(create=fake_create))
    assert ping_embed(client, "gemini-embedding-001") == 3
