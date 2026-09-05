"""Live Mistral chat. Skips if MISTRAL_API_KEY is missing."""

from providers import chat_client, model_for, ping_chat, skip_if_unconfigured


def test_mistral_chat_api_responds():
    skip_if_unconfigured("mistral")
    text = ping_chat(chat_client("mistral"), model_for("mistral"))
    assert text
