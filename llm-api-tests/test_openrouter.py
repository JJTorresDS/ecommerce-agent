"""Live OpenRouter chat. Skips if OPEN_ROUTER_API_KEY is missing."""

from providers import chat_client, model_for, ping_chat, skip_if_unconfigured


def test_openrouter_chat_api_responds():
    skip_if_unconfigured("openrouter")
    text = ping_chat(chat_client("openrouter"), model_for("openrouter"))
    assert text
