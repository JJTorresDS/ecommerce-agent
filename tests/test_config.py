import pytest

from ecommerce_agent.config import (
    DEFAULT_EMBEDDING_MODELS,
    EMBEDDING_PROVIDER,
    GEMINI_OPENAI_BASE_URL,
    LANGFUSE_ENVIRONMENT,
    LANGFUSE_TRACING,
    LLM_PROVIDER,
    LOCAL_MODEL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    Settings,
    _load_settings,
)


def test_settings_uses_generic_model_and_key_fields():
    names = set(Settings.__dataclass_fields__)
    assert {"llm_provider", "model", "api_key"} <= names
    assert {"embedding_provider", "embedding_model", "embedding_api_key"} <= names
    assert names.isdisjoint(
        {
            "local_model",
            "ollama_model",
            "ollama_base_url",
            "openrouter_model",
            "openai_model",
            "openai_embedding_model",
            "openai_api_key",
            "open_router_api_key",
        }
    )


def test_provider_base_urls_are_module_constants():
    assert OLLAMA_BASE_URL.rstrip("/").endswith("11434/v1")
    assert "openrouter.ai" in OPENROUTER_BASE_URL
    assert "api.openai.com" in OPENAI_BASE_URL
    assert "generativelanguage.googleapis.com" in GEMINI_OPENAI_BASE_URL


def test_llm_and_embedding_providers_are_config_constants():
    assert LLM_PROVIDER == "openai"
    assert EMBEDDING_PROVIDER == "gemini"
    assert LOCAL_MODEL is False


def test_env_does_not_override_provider_constants(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LOCAL_MODEL", "true")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hf")

    loaded = _load_settings()

    assert loaded.llm_provider == "openai"
    assert loaded.embedding_provider == "gemini"


def test_load_settings_reads_secrets_and_model_from_env(monkeypatch):
    monkeypatch.setenv("MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_MODEL", "should-not-win")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EMBEDDING_MODEL", "gemini-embedding-001")

    loaded = _load_settings()

    assert loaded.llm_provider == LLM_PROVIDER
    assert loaded.model == "gpt-4o"
    assert loaded.api_key == "sk-test"
    assert loaded.embedding_provider == EMBEDDING_PROVIDER
    assert loaded.embedding_model == DEFAULT_EMBEDDING_MODELS[EMBEDDING_PROVIDER]
    assert loaded.embedding_api_key == "gemini-test"


def test_langfuse_tracing_is_a_config_constant():
    assert LANGFUSE_TRACING is True
    assert LANGFUSE_ENVIRONMENT == "development"


def test_langfuse_enabled_requires_keys_from_env(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    assert _load_settings().langfuse_enabled is False

    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    loaded = _load_settings()
    assert loaded.langfuse_enabled is True
    assert loaded.langfuse_public_key == "pk-lf-test"


def test_load_settings_rejects_embedding_model_for_other_provider(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "BAAI/bge-m3")

    with pytest.raises(ValueError, match=r"Provider model mismatch.*config\.py"):
        _load_settings()
