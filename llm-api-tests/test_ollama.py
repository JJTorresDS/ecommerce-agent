"""Live Ollama chat. Skips if the local server is not reachable."""

import pytest
from openai import APIConnectionError

from providers import chat_client, model_for, ping_chat


def test_ollama_chat_api_responds():
    try:
        text = ping_chat(chat_client("ollama"), model_for("ollama"))
    except APIConnectionError as exc:
        pytest.skip(f"Ollama is not reachable: {exc}")
    assert text
