import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
from sentence_transformers import SentenceTransformer

from ecommerce_agent.embeddings.base import EmbeddingProvider


class HFEmbeddingProvider(EmbeddingProvider):
    """Local embeddings via sentence-transformers (default: BAAI/bge-m3)."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.embedding_dim = self._model.get_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=32)
