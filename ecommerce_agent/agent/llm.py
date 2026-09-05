"""Ollama, OpenRouter, OpenAI, or Mistral client for the Agents SDK."""

from agents import Model, OpenAIChatCompletionsModel, OpenAIResponsesModel
from openai import AsyncOpenAI

from ecommerce_agent.config import (
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    settings,
)


def build_model() -> Model:
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
    elif provider == "mistral":
        client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=MISTRAL_BASE_URL,
        )
        return OpenAIChatCompletionsModel(
            model=settings.model,
            openai_client=client,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            "Options: ollama, openrouter, openai, mistral"
        )

    return OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )
