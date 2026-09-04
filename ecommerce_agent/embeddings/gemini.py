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
        )
        ordered = sorted(response.data, key=lambda d: d.index)
        return np.array([d.embedding for d in ordered])

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)
