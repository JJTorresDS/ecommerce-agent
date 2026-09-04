from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    """Common interface every embedding backend must implement."""

    model_name: str
    embedding_dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of strings, returning an (N, embedding_dim) array."""
        raise NotImplementedError

    def similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """Similarity between two embedding vectors.

        Default implementation assumes both vectors are already unit
        length, so cosine similarity reduces to a plain dot product.
        """
        return float(np.dot(vec_a, vec_b))
