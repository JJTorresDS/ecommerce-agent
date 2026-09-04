"""Ollama, OpenRouter, or OpenAI client for the Agents SDK."""

from agents import OpenAIResponsesModel
from openai import AsyncOpenAI

from ecommerce_agent.config import (
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    settings,
)


def build_model() -> OpenAIResponsesModel:
    provider = settings.llm_provider
    if provider == "openai":
        client = AsyncOpenAI(api_key=settings.api_key, base_url=OPENAI_BASE_URL)
    elif provider == "ollama":
        client = AsyncOpenAI(
            base_url=OLLAMA_BASE_URL, api_key=settings.api_key or "ollama"
        )
    elif provider == "openrouter":
        client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=settings.api_key,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            "Options: ollama, openrouter, openai"
        )

    return OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )
