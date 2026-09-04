from types import SimpleNamespace
from unittest.mock import Mock

from ecommerce_agent.agent import llm as llm_mod
from ecommerce_agent.config import OPENAI_BASE_URL, OPENROUTER_BASE_URL


def _settings(**overrides) -> SimpleNamespace:
    values = dict(
        llm_provider="openrouter",
        model="nvidia/nemotron-3.5-lightning:free",
        api_key="or-key",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_build_model_uses_openai_when_provider_is_openai(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setattr(
        llm_mod,
        "settings",
        _settings(llm_provider="openai", model="gpt-4o-mini", api_key="sk-test"),
    )
    monkeypatch.setattr(llm_mod, "AsyncOpenAI", fake_client)

    model = llm_mod.build_model()

    assert captured["api_key"] == "sk-test"
    assert captured.get("base_url") in (None, OPENAI_BASE_URL)
    assert model.model == "gpt-4o-mini"


def test_build_model_uses_ollama_when_provider_is_ollama(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setattr(
        llm_mod,
        "settings",
        _settings(
            llm_provider="ollama",
            model="qwen2.5:7b",
            api_key="ollama",
        ),
    )
    monkeypatch.setattr(llm_mod, "AsyncOpenAI", fake_client)

    model = llm_mod.build_model()

    assert captured["api_key"] == "ollama"
    assert captured["base_url"] == llm_mod.OLLAMA_BASE_URL
    assert model.model == "qwen2.5:7b"


def test_build_model_uses_openrouter_when_provider_is_openrouter(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return Mock()

    monkeypatch.setattr(llm_mod, "settings", _settings(llm_provider="openrouter"))
    monkeypatch.setattr(llm_mod, "AsyncOpenAI", fake_client)

    model = llm_mod.build_model()

    assert captured["api_key"] == "or-key"
    assert captured["base_url"] == OPENROUTER_BASE_URL
    assert model.model == "nvidia/nemotron-3.5-lightning:free"
