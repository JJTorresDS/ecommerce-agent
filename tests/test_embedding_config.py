from types import SimpleNamespace

import pytest

from ecommerce_agent.config import DEFAULT_EMBEDDING_MODELS
from ecommerce_agent.embeddings.gemini import GeminiEmbeddingProvider
from ecommerce_agent.embeddings.hf import HFEmbeddingProvider
from ecommerce_agent.embeddings.openai import OpenAIEmbeddingProvider


def test_embedding_model_defaults_live_in_config():
    assert DEFAULT_EMBEDDING_MODELS["gemini"] == "gemini-embedding-001"
    assert DEFAULT_EMBEDDING_MODELS["openai"] == "text-embedding-3-small"
    assert DEFAULT_EMBEDDING_MODELS["hf"] == "BAAI/bge-m3"
    for cls in (GeminiEmbeddingProvider, OpenAIEmbeddingProvider, HFEmbeddingProvider):
        assert not hasattr(cls, "DEFAULT_MODEL")


def test_gemini_rejects_provider_mismatch(monkeypatch):
    monkeypatch.setattr(
        "ecommerce_agent.embeddings.gemini.settings",
        SimpleNamespace(
            embedding_provider="hf",
            embedding_model="BAAI/bge-m3",
            embedding_api_key="unused",
        ),
    )
    with pytest.raises(ValueError, match=r"Provider model mismatch.*config\.py"):
        GeminiEmbeddingProvider(api_key="test")


def test_openai_rejects_provider_mismatch(monkeypatch):
    monkeypatch.setattr(
        "ecommerce_agent.embeddings.openai.settings",
        SimpleNamespace(
            embedding_provider="gemini",
            embedding_model="gemini-embedding-001",
            embedding_api_key="unused",
        ),
    )
    with pytest.raises(ValueError, match=r"Provider model mismatch.*config\.py"):
        OpenAIEmbeddingProvider(api_key="test")


def test_hf_rejects_provider_mismatch(monkeypatch):
    monkeypatch.setattr(
        "ecommerce_agent.embeddings.hf.settings",
        SimpleNamespace(
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
        ),
    )
    with pytest.raises(ValueError, match=r"Provider model mismatch.*config\.py"):
        HFEmbeddingProvider()
