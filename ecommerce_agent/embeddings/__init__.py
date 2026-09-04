"""Embedding providers. The HF/Gemini client is created on first use."""

from __future__ import annotations

from ecommerce_agent.config import settings
from ecommerce_agent.embeddings.base import EmbeddingProvider
from ecommerce_agent.embeddings.gemini import GeminiEmbeddingProvider
from ecommerce_agent.embeddings.hf import HFEmbeddingProvider

_PROVIDERS = {
    "hf": HFEmbeddingProvider,
    "gemini": GeminiEmbeddingProvider,
}

_instance: EmbeddingProvider | None = None


def get_provider(name: str | None = None) -> EmbeddingProvider:
    """Return an embedding provider.

    With no `name`, returns the process-wide default (from
    EMBEDDING_PROVIDER / "hf") and creates it once. Passing `name`
    always builds a new instance of that backend.
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
