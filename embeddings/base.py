from abc import ABC, abstractmethod

import numpy as np

class EmbeddingProvider(ABC):
    """Common interface every embedding backend must implement.

    Swapping providers (HF <-> Gemini) should only ever mean swapping
    which class gets instantiated in embeddings/__init__.py -- nothing
    in vector_store.py or embeddings/ingest.py should need to change.
    """

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
        Override this in a subclass if a provider's vectors aren't
        guaranteed to be normalized (see gemini.py for an example).
        """
        return float(np.dot(vec_a, vec_b))