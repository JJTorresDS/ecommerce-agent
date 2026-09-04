import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
from sentence_transformers import SentenceTransformer

from ecommerce_agent.config import require_embedding_provider, settings
from ecommerce_agent.embeddings.base import EmbeddingProvider


class HFEmbeddingProvider(EmbeddingProvider):
    """Local embeddings via sentence-transformers."""

    def __init__(self):
        self.model_name = require_embedding_provider("hf", settings)
        self._model = SentenceTransformer(self.model_name)
        self.embedding_dim = self._model.get_embedding_dimension()

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, batch_size=32)
