"""Evaluate the ecommerce agent against FAQ gold answers using MLflow.

Uses `evals/datasets/llm_eval_dataset.json` (inputs.question /
expectations.expected_response) and MLflow's built-in Correctness scorer.

`predict_fn` runs `build_agent()` (same tools and instructions as `/ask`).
Rows run one at a time with a 1 second pause after each prediction.
`--provider` and `--experiment` are required. Optional `--n` evaluates only
the first n dataset rows. If the experiment exists, the run is added there;
otherwise a new experiment is created. Run names are
`llm-eval-{provider}-{model}` from the built agent.

    uv run python evals/evaluate_llm_response.py --provider mistral --experiment ecommerce-agent-llm_eval
    uv run python evals/evaluate_llm_response.py --provider openai --experiment ecommerce-agent-llm_eval
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = "1"

import mlflow
from agents import Agent, Runner
from mlflow.genai.scorers import Correctness

from ecommerce_agent.agent import llm as llm_mod
from ecommerce_agent.agent.factory import build_agent
from ecommerce_agent.config import (
    MISTRAL_BASE_URL,
    OLLAMA_BASE_URL,
    OPENAI_BASE_URL,
    OPENROUTER_BASE_URL,
    PROJECT_ROOT,
    _DEFAULT_CHAT_MODELS,
    _api_key,
)

CHAT_PROVIDERS = ("openai", "openrouter", "mistral", "ollama")
DEFAULT_DATASET = PROJECT_ROOT / "evals" / "datasets" / "llm_eval_dataset.json"
DEFAULT_TRACKING_URI = "http://127.0.0.1:5000"
PAUSE_SECONDS = 1
MAX_WORKERS = 1

_PROVIDER_BASE_URLS = (
    ("mistral", MISTRAL_BASE_URL),
    ("openrouter", OPENROUTER_BASE_URL),
    ("ollama", OLLAMA_BASE_URL),
    ("openai", OPENAI_BASE_URL),
)


@dataclass(frozen=True)
class AgentLlmIdentity:
    provider: str
    model: str

    @property
    def run_name(self) -> str:
        return f"llm-eval-{self.provider}-{self.model}"


def load_eval_dataset(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{path} must be a non-empty JSON array")
    return payload


def limit_eval_dataset(rows: list[dict], n: int | None) -> list[dict]:
    if n is None:
        return rows
    if n < 1:
        raise ValueError("--n must be at least 1")
    return rows[:n]


def resolve_model(provider: str) -> str:
    return _DEFAULT_CHAT_MODELS[provider]


def provider_from_base_url(base_url: str) -> str | None:
    haystack = str(base_url).rstrip("/").lower()
    for name, configured in _PROVIDER_BASE_URLS:
        needle = configured.rstrip("/").lower()
        if needle and needle in haystack:
            return name
    return None


def provider_and_model_from_agent(
    agent: Any,
    fallback_provider: str | None = None,
) -> AgentLlmIdentity:
    model_obj = getattr(agent, "model", None)
    model_id = str(getattr(model_obj, "model", "") or "")
    client = getattr(model_obj, "_client", None)
    base_url = str(getattr(client, "base_url", "") or "")
    provider = provider_from_base_url(base_url) or fallback_provider or ""
    return AgentLlmIdentity(provider=provider, model=model_id)


def new_run_stats() -> dict[str, Any]:
    return {
        "latency_ms": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }


def usage_from_result(result: Any) -> dict[str, int]:
    usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def build_eval_agent(provider: str) -> Agent:
    base = build_agent()
    previous = llm_mod.settings
    llm_mod.settings = SimpleNamespace(
        llm_provider=provider,
        model=resolve_model(provider),
        api_key=_api_key(provider),
    )
    try:
        agent_model = llm_mod.build_model()
    finally:
        llm_mod.settings = previous

    return Agent(
        name=base.name,
        instructions=base.instructions,
        model=agent_model,
        hooks=base.hooks,
        tools=base.tools,
    )


def make_predict_fn(agent: Agent, stats: dict[str, Any]):
    def predict_fn(question: str) -> str:
        started = time.perf_counter()
        result = Runner.run_sync(agent, question)
        stats["latency_ms"].append((time.perf_counter() - started) * 1000)
        usage = usage_from_result(result)
        stats["input_tokens"] += usage["input_tokens"]
        stats["output_tokens"] += usage["output_tokens"]
        stats["total_tokens"] += usage["total_tokens"]
        time.sleep(PAUSE_SECONDS)
        return str(result.final_output or "")

    return predict_fn


def log_run_attributes(
    *,
    provider: str,
    model: str,
    stats: dict[str, Any],
    n: int,
) -> None:
    mlflow.log_param("provider", provider)
    mlflow.log_param("model", model)
    mlflow.log_param("n", n)
    latencies = stats["latency_ms"]
    mlflow.log_metric(
        "latency_ms",
        (sum(latencies) / len(latencies)) if latencies else 0.0,
    )
    mlflow.log_metric("input_tokens", stats["input_tokens"])
    mlflow.log_metric("output_tokens", stats["output_tokens"])
    mlflow.log_metric("total_tokens", stats["total_tokens"])


def ensure_experiment(name: str) -> None:
    if mlflow.get_experiment_by_name(name) is None:
        mlflow.create_experiment(name)
    mlflow.set_experiment(name)


def setup_mlflow(experiment: str) -> None:
    os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = str(MAX_WORKERS)
    uri = os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI)
    mlflow.set_tracking_uri(uri)
    ensure_experiment(experiment)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the ecommerce agent against FAQ ground truth."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--provider",
        required=True,
        choices=CHAT_PROVIDERS,
        help="Agent LLM backend (e.g. mistral). Model is taken from the built agent.",
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="MLflow experiment name. Reuses it if it exists; otherwise creates it.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="Optional. Evaluate only the first n dataset rows.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    setup_mlflow(args.experiment)
    eval_dataset = limit_eval_dataset(load_eval_dataset(args.dataset), args.n)
    agent = build_eval_agent(args.provider)
    identity = provider_and_model_from_agent(
        agent, fallback_provider=args.provider
    )
    stats = new_run_stats()
    predict_fn = make_predict_fn(agent, stats)
    print(
        f"Evaluating agent experiment={args.experiment} "
        f"run={identity.run_name} provider={identity.provider} "
        f"model={identity.model} n={len(eval_dataset)}"
    )

    with mlflow.start_run(run_name=identity.run_name):
        try:
            mlflow.genai.evaluate(
                data=eval_dataset,
                predict_fn=predict_fn,
                scorers=[Correctness()],
            )
        finally:
            log_run_attributes(
                provider=identity.provider,
                model=identity.model,
                stats=stats,
                n=len(eval_dataset),
            )


if __name__ == "__main__":
    main()
