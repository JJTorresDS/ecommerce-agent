"""Live Gemini embeddings. Skips if GEMINI_API_KEY is missing."""

from providers import (
    embed_client,
    embed_model_for,
    ping_embed,
    skip_if_unconfigured,
)


def test_gemini_embeddings_api_responds():
    skip_if_unconfigured("gemini")
    width = ping_embed(
        embed_client("gemini"),
        embed_model_for("gemini"),
        dimensions=768,
    )
    assert width > 0
