from unittest.mock import Mock

import numpy as np

from ecommerce_agent.embeddings.gemini import GeminiEmbeddingProvider


def _provider_with_data(items: list) -> GeminiEmbeddingProvider:
    provider = GeminiEmbeddingProvider(api_key="test")
    provider._client = Mock()
    provider._client.embeddings.create.return_value = Mock(data=items)
    return provider


def test_embed_when_gemini_omits_or_mixes_index():
    """Gemini's OpenAI-compatible API may leave `index` as None."""
    items = [
        Mock(index=None, embedding=[1.0, 0.0]),
        Mock(index=1, embedding=[0.0, 1.0]),
    ]
    provider = _provider_with_data(items)

    result = provider.embed(["kid love vest", "windbreaker"])

    np.testing.assert_array_equal(result, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_embed_sorts_by_index_when_all_present():
    items = [
        Mock(index=1, embedding=[0.0, 1.0]),
        Mock(index=0, embedding=[1.0, 0.0]),
    ]
    provider = _provider_with_data(items)

    result = provider.embed(["a", "b"])

    np.testing.assert_array_equal(result, np.array([[1.0, 0.0], [0.0, 1.0]]))


def test_embed_truncates_native_3072_to_declared_768():
    native = np.arange(3072, dtype=float)
    items = [Mock(index=0, embedding=native.tolist())]
    provider = _provider_with_data(items)

    result = provider.embed(["KID LOVE VEST"])

    assert result.shape == (1, 768)
    expected = native[:768]
    expected = expected / np.linalg.norm(expected)
    np.testing.assert_allclose(result[0], expected)
    kwargs = provider._client.embeddings.create.call_args.kwargs
    assert kwargs["dimensions"] == 768
