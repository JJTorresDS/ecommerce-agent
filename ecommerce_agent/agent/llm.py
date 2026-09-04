"""Ollama vs OpenRouter client for the Agents SDK."""

from agents import OpenAIResponsesModel
from openai import AsyncOpenAI

from ecommerce_agent.config import settings


def build_model() -> OpenAIResponsesModel:
    if settings.local_model:
        client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key="ollama",
        )
        model_name = settings.ollama_model
    else:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.open_router_api_key,
        )
        model_name = settings.openrouter_model

    return OpenAIResponsesModel(
        model=model_name,
        openai_client=client,
    )
