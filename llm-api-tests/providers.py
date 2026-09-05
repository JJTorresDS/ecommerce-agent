"""Shared clients for live LLM API smoke tests.

These hit the real network. `uv run pytest` does not collect this folder.
Run a provider with:

    uv run pytest llm-api-tests/test_mistral.py -v
"""

from __future__ import annotations

import os

os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_DB", "pyrolabs-local")

import pytest
from openai import OpenAI

from ecommerce_agent.config import (
    DEFAULT_EMBEDDING_MODELS,
    GEMINI_OPENAI_BASE_URL,
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    _DEFAULT_CHAT_MODELS,
    _api_key,
)

CHAT_PROVIDERS = ("openai", "openrouter", "mistral", "ollama")
EMBED_PROVIDERS = ("openai", "gemini")

_BASE_URLS = {
    "openai": OPENAI_BASE_URL,
    "openrouter": OPENROUTER_BASE_URL,
    "mistral": MISTRAL_BASE_URL,
    "ollama": OLLAMA_BASE_URL,
    "gemini": GEMINI_OPENAI_BASE_URL,
}

_CHAT_MODEL_ENV = {
    "openai": "OPENAI_MODEL",
    "ollama": "OLLAMA_MODEL",
    "openrouter": "OPENROUTER_MODEL",
    "mistral": "MISTRAL_MODEL",
}

_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPEN_ROUTER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

PING = "Reply with the single word pong."


def base_url_for(provider: str) -> str:
    try:
        return _BASE_URLS[provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Chat: {', '.join(CHAT_PROVIDERS)}. "
            f"Embeddings: {', '.join(EMBED_PROVIDERS)}."
        ) from exc


def model_for(provider: str) -> str:
    env_name = _CHAT_MODEL_ENV[provider]
    if value := os.getenv(env_name):
        return value
    return _DEFAULT_CHAT_MODELS[provider]


def embed_model_for(provider: str) -> str:
    return DEFAULT_EMBEDDING_MODELS[provider]


def key_for(provider: str) -> str | None:
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY")
    return _api_key(provider)


def skip_if_unconfigured(provider: str) -> None:
    if provider == "ollama":
        return
    env_name = _KEY_ENV[provider]
    if not os.getenv(env_name):
        pytest.skip(f"{env_name} is not set")


def chat_client(provider: str) -> OpenAI:
    if provider not in CHAT_PROVIDERS:
        raise ValueError(
            f"Unknown chat provider '{provider}'. Options: {', '.join(CHAT_PROVIDERS)}"
        )
    return OpenAI(
        api_key=key_for(provider) or "ollama",
        base_url=base_url_for(provider),
        timeout=30.0,
    )


def embed_client(provider: str) -> OpenAI:
    if provider not in EMBED_PROVIDERS:
        raise ValueError(
            f"Unknown embedding provider '{provider}'. "
            f"Options: {', '.join(EMBED_PROVIDERS)}"
        )
    return OpenAI(
        api_key=key_for(provider),
        base_url=base_url_for(provider),
        timeout=30.0,
    )


def ping_chat(client: OpenAI, model: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PING}],
        max_tokens=16,
        temperature=0,
    )
    return (response.choices[0].message.content or "").strip()


def ping_embed(
    client: OpenAI,
    model: str,
    dimensions: int | None = None,
) -> int:
    kwargs: dict = {"input": ["ping"], "model": model}
    if dimensions is not None:
        kwargs["dimensions"] = dimensions
    response = client.embeddings.create(**kwargs)
    return len(response.data[0].embedding)
