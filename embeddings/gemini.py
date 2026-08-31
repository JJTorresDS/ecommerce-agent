import os

import numpy as np
from openai import OpenAI

from embeddings.base import EmbeddingProvider

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Embeddings via Gemini's OpenAI-compatible endpoint.

    Uses the `openai` package pointed at Google's compatibility base URL,
    rather than the separate google-genai SDK -- this keeps only one
    HTTP client library in the project if you're already using `openai`
    elsewhere (e.g. for agent.py).

    Requires a Gemini API key. Pass it explicitly or set GEMINI_API_KEY
    in the environment.
    """

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
        # response.data isn't guaranteed to preserve input order across
        # every OpenAI-compatible backend -- sort by `index` to be safe.
        ordered = sorted(response.data, key=lambda d: d.index)
        return np.array([d.embedding for d in ordered])

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        # Not guaranteed to be unit-normalized (e.g. if the endpoint
        # truncates dimensions via MRL), so normalize explicitly rather
        # than assuming a plain dot product is a valid cosine similarity.
        denom = np.linalg.norm(vec_a) * np.linalg.norm(vec_b)
        if denom == 0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / denom)