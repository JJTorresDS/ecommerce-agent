"""Langfuse tracing for the OpenAI Agents SDK."""

from __future__ import annotations

import os
from typing import Optional

from agents import set_tracing_disabled
from langfuse import Langfuse
from langfuse.types import (
    MaskOtelSpansParams,
    MaskOtelSpansResult,
    OtelSpanPatch,
)
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

from ecommerce_agent.config import (
    LANGFUSE_BASE_URL,
    LANGFUSE_ENVIRONMENT,
    settings,
)

_instrumented = False
_client: Langfuse | None = None
_SECRET_ATTRIBUTE_TOKENS = ("public_key", "secret", "api_key", "password")


def _should_redact_attribute(key: str) -> bool:
    lowered = key.lower()
    return any(token in lowered for token in _SECRET_ATTRIBUTE_TOKENS)


def mask_otel_spans(*, params: MaskOtelSpansParams) -> Optional[MaskOtelSpansResult]:
    patches: dict = {}
    for identifier, span in params.spans.items():
        replacements = {
            key: "***"
            for key, value in span.attributes.items()
            if _should_redact_attribute(key) and value not in (None, "***")
        }
        if replacements:
            patches[identifier] = OtelSpanPatch(set_attributes=replacements)
    return MaskOtelSpansResult(span_patches=patches) if patches else None


def get_client() -> Langfuse:
    global _client
    if _client is None:
        os.environ.setdefault("LANGFUSE_BASE_URL", LANGFUSE_BASE_URL)
        os.environ.setdefault(
            "LANGFUSE_HOST", os.environ.get("LANGFUSE_BASE_URL", LANGFUSE_BASE_URL)
        )
        os.environ.setdefault("OTEL_SERVICE_NAME", "ecommerce-agent")
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=os.environ.get("LANGFUSE_BASE_URL", LANGFUSE_BASE_URL),
            environment=LANGFUSE_ENVIRONMENT,
            mask_otel_spans=mask_otel_spans,
        )
    return _client


def setup_tracing() -> None:
    """Instrument Agents SDK runs and send them to Langfuse when keys are set."""
    global _instrumented
    set_tracing_disabled(not settings.agent_tracing)
    if not settings.langfuse_enabled or _instrumented:
        return

    os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", LANGFUSE_ENVIRONMENT)
    OpenAIAgentsInstrumentor().instrument()
    get_client()
    _instrumented = True


def flush_tracing() -> None:
    if settings.langfuse_enabled:
        get_client().flush()
