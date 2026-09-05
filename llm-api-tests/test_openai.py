"""Live OpenAI chat + embeddings. Skips if OPENAI_API_KEY is missing."""

from providers import (
    chat_client,
    embed_client,
    embed_model_for,
    model_for,
    ping_chat,
    ping_embed,
    skip_if_unconfigured,
)


def test_openai_chat_api_responds():
    skip_if_unconfigured("openai")
    text = ping_chat(chat_client("openai"), model_for("openai"))
    assert text


def test_openai_embeddings_api_responds():
    skip_if_unconfigured("openai")
    width = ping_embed(
        embed_client("openai"),
        embed_model_for("openai"),
        dimensions=1536,
    )
    assert width > 0
