import os

import numpy as np
from openai import OpenAI

from ecommerce_agent.embeddings.base import EmbeddingProvider

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embeddings via Gemini's OpenAI-compatible endpoint."""

    def __init__(
        self,
        model_name: str = "gemini-embedding-001",
        api_key: str | None = None,
        embedding_dim: int = 768,
    ):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self._client = OpenAI(
            api_key=api_key or os.environ["GEMINI_API_KEY"],
            base_url=GEMINI_OPENAI_BASE_URL,
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        response = self._client.embeddings.create(
            input=texts,
            model=self.model_name,
            dimensions=self.embedding_dim,
        )
        items = list(response.data)
        if items and all(getattr(item, "index", None) is not None for item in items):
            items = sorted(items, key=lambda item: item.index)
        vectors = np.array([item.embedding for item in items], dtype=float)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] > self.embedding_dim:
            vectors = vectors[:, : self.embedding_dim]
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            vectors = vectors / norms
        return vectors

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)
