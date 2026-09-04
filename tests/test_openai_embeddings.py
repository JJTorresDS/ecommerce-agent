from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from ecommerce_agent.config import DEFAULT_EMBEDDING_MODELS
from ecommerce_agent.embeddings import _PROVIDERS
from ecommerce_agent.embeddings.openai import OpenAIEmbeddingProvider


@pytest.fixture(autouse=True)
def openai_settings(monkeypatch):
    monkeypatch.setattr(
        "ecommerce_agent.embeddings.openai.settings",
        SimpleNamespace(
            embedding_provider="openai",
            embedding_model=DEFAULT_EMBEDDING_MODELS["openai"],
            embedding_api_key="test",
        ),
    )


def _provider_with_data(items: list) -> OpenAIEmbeddingProvider:
    provider = OpenAIEmbeddingProvider(api_key="test")
    provider._client = Mock()
    provider._client.embeddings.create.return_value = Mock(data=items)
    return provider


def test_openai_is_a_registered_embedding_provider():
    assert "openai" in _PROVIDERS
    assert _PROVIDERS["openai"] is OpenAIEmbeddingProvider


def test_openai_embed_sorts_by_index_when_all_present():
    items = [
        Mock(index=1, embedding=[0.0, 1.0]),
        Mock(index=0, embedding=[1.0, 0.0]),
    ]
    provider = _provider_with_data(items)

    result = provider.embed(["kid love vest", "windbreaker"])

    np.testing.assert_array_equal(result, np.array([[1.0, 0.0], [0.0, 1.0]]))
    kwargs = provider._client.embeddings.create.call_args.kwargs
    assert kwargs["model"] == DEFAULT_EMBEDDING_MODELS["openai"]
    assert kwargs["dimensions"] == 1536


def test_openai_embed_requests_declared_dimensions():
    items = [Mock(index=0, embedding=[0.1] * 1536)]
    provider = _provider_with_data(items)

    result = provider.embed(["KID LOVE VEST"])

    assert result.shape == (1, 1536)
    kwargs = provider._client.embeddings.create.call_args.kwargs
    assert kwargs["dimensions"] == 1536
