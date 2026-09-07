"""Compare latency and token usage across integrated chat providers.

Traces and metrics go to the MLflow experiment ``ecommerce-agent-latency-tokens``.
Start the UI with ``uv run mlflow server`` and open http://127.0.0.1:5000.

    uv run python evals/evaluate_llm_provider_latency.py
    uv run python evals/evaluate_llm_provider_latency.py --provider mistral
"""

from __future__ import annotations

import argparse
import os
import time
from typing import Any

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
from mlflow.entities import SpanType
from mlflow.openai import autolog as openai_autolog
from openai import OpenAI

from ecommerce_agent.config import (
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    _DEFAULT_CHAT_MODELS,
    _api_key,
)

CHAT_PROVIDERS = ("openai", "openrouter", "mistral", "ollama")
PROMPT = "Hi, I want to buy a gift for my 2.5 year old nephew"
EXPERIMENT_NAME = "ecommerce-agent-latency-tokens"
DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"

_BASE_URLS = {
    "openai": OPENAI_BASE_URL,
    "openrouter": OPENROUTER_BASE_URL,
    "mistral": MISTRAL_BASE_URL,
    "ollama": OLLAMA_BASE_URL,
}

_CHAT_MODEL_ENV = {
    "openai": "OPENAI_MODEL",
    "ollama": "OLLAMA_MODEL",
    "openrouter": "OPENROUTER_MODEL",
    "mistral": "MISTRAL_MODEL",
}


def model_for(provider: str) -> str:
    env_name = _CHAT_MODEL_ENV[provider]
    if value := os.getenv(env_name):
        return value
    return _DEFAULT_CHAT_MODELS[provider]


def is_configured(provider: str) -> bool:
    if provider == "ollama":
        return True
    return bool(_api_key(provider))


def chat_client(provider: str) -> OpenAI:
    if provider not in CHAT_PROVIDERS:
        raise ValueError(
            f"Unknown chat provider '{provider}'. Options: {', '.join(CHAT_PROVIDERS)}"
        )
    return OpenAI(
        api_key=_api_key(provider) or "ollama",
        base_url=_BASE_URLS[provider],
        timeout=60.0,
    )


def usage_from_response(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def setup_mlflow() -> None:
    uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(EXPERIMENT_NAME)
    openai_autolog()


def evaluate_provider(provider: str) -> dict[str, Any]:
    model = model_for(provider)
    with mlflow.start_span(name=f"llm.{provider}", span_type=SpanType.LLM) as span:
        span.set_inputs({"provider": provider, "model": model, "prompt": PROMPT})
        client = chat_client(provider)
        started = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": PROMPT}],
        )
        latency_ms = (time.perf_counter() - started) * 1000
        output = (response.choices[0].message.content or "").strip()
        result = {
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "output": output,
            **usage_from_response(response),
        }
        span.set_outputs(result)
        return result


def _log_result_metrics(result: dict[str, Any]) -> None:
    mlflow.log_param("provider", result["provider"])
    mlflow.log_param("model", result["model"])
    mlflow.log_metric("latency_ms", result["latency_ms"])
    for name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = result.get(name)
        if value is not None:
            mlflow.log_metric(name, value)


def run_eval(providers: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    setup_mlflow()
    selected = providers or CHAT_PROVIDERS
    results: list[dict[str, Any]] = []
    with mlflow.start_run(run_name="llm-latency-tokens"):
        mlflow.log_param("prompt", PROMPT)
        for provider in selected:
            if not is_configured(provider):
                results.append(
                    {
                        "provider": provider,
                        "skipped": True,
                        "reason": "missing api key",
                    }
                )
                continue
            with mlflow.start_run(run_name=provider, nested=True):
                try:
                    result = evaluate_provider(provider)
                    _log_result_metrics(result)
                    results.append(result)
                except Exception as exc:
                    results.append({"provider": provider, "error": str(exc)})
                    mlflow.log_param("error", str(exc)[:500])
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate chat provider latency and token usage (MLflow traces)."
    )
    parser.add_argument(
        "--provider",
        action="append",
        choices=CHAT_PROVIDERS,
        help="Provider to evaluate (repeatable). Default: all configured providers.",
    )
    args = parser.parse_args()
    providers = tuple(args.provider) if args.provider else None
    results = run_eval(providers=providers)
    for row in results:
        provider = row["provider"]
        if row.get("skipped"):
            print(f"{provider}: skipped ({row.get('reason')})")
            continue
        if row.get("error"):
            print(f"{provider}: error {row['error']}")
            continue
        tokens = row.get("total_tokens")
        token_part = f" tokens={tokens}" if tokens is not None else ""
        print(
            f"{provider} ({row['model']}): "
            f"{row['latency_ms']:.0f} ms{token_part}"
        )


if __name__ == "__main__":
    main()
