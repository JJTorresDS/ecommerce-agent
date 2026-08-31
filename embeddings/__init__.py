import os

from embeddings.base import EmbeddingProvider
from embeddings.hf import HFEmbeddingProvider
from embeddings.gemini import GeminiEmbeddingProvider

_PROVIDERS = {
    "hf": HFEmbeddingProvider,
    "gemini": GeminiEmbeddingProvider,
}


def get_provider(name: str | None = None) -> EmbeddingProvider:
    """Instantiate an embedding provider by name.

    `name` falls back to the EMBEDDING_PROVIDER environment variable,
    then to "hf" if neither is set. Raises ValueError on an unknown name
    so a typo'd env var fails loudly instead of silently picking a
    default.
    """
    name = name or os.environ.get("EMBEDDING_PROVIDER", "hf")#default to hf
    try:
        provider_cls = _PROVIDERS[name]
    except KeyError:
        raise ValueError(
            f"Unknown embedding provider '{name}'. Options: {list(_PROVIDERS)}"
        )
    return provider_cls()


# Process-wide default instance. Both vector_store.py and
# embeddings/ingest.py import this rather than calling get_provider()
# themselves, so the (potentially slow, e.g. HF model load) provider is
# only instantiated once per process instead of once per import site.
#
#     from embeddings import provider
#     provider.embed(["some text"])
provider = get_provider()