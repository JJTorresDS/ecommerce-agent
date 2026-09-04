"""Embedding providers. The HF/Gemini/OpenAI client is created on first use."""

from __future__ import annotations

from ecommerce_agent.config import settings
from ecommerce_agent.embeddings.base import EmbeddingProvider
from ecommerce_agent.embeddings.gemini import GeminiEmbeddingProvider
from ecommerce_agent.embeddings.hf import HFEmbeddingProvider
from ecommerce_agent.embeddings.openai import OpenAIEmbeddingProvider

_PROVIDERS = {
    "hf": HFEmbeddingProvider,
    "gemini": GeminiEmbeddingProvider,
    "openai": OpenAIEmbeddingProvider,
}

_instance: EmbeddingProvider | None = None


def get_provider(name: str | None = None) -> EmbeddingProvider:
    """Return an embedding provider.

    With no `name`, returns the process-wide default from
    `config.EMBEDDING_PROVIDER` and creates it once. Passing `name`
    always builds a new instance of that backend, and raises if it
    does not match `EMBEDDING_PROVIDER`.
    """
    global _instance
    if name is not None:
        try:
            return _PROVIDERS[name]()
        except KeyError:
            raise ValueError(
                f"Unknown embedding provider '{name}'. Options: {list(_PROVIDERS)}"
            ) from None

    if _instance is None:
        provider_name = settings.embedding_provider
        try:
            _instance = _PROVIDERS[provider_name]()
        except KeyError:
            raise ValueError(
                f"Unknown embedding provider '{provider_name}'. "
                f"Options: {list(_PROVIDERS)}"
            ) from None
    return _instance


class _LazyProvider:
    """Attribute proxy so `provider.embed(...)` stays valid without import-time load."""

    def __getattr__(self, name: str):
        return getattr(get_provider(), name)


provider = _LazyProvider()
