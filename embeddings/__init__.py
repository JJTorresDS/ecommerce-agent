"""Backward-compatible re-export of embedding providers."""

from ecommerce_agent.embeddings import get_provider, provider
from ecommerce_agent.embeddings.base import EmbeddingProvider
from ecommerce_agent.embeddings.gemini import GeminiEmbeddingProvider
from ecommerce_agent.embeddings.hf import HFEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "HFEmbeddingProvider",
    "get_provider",
    "provider",
]
