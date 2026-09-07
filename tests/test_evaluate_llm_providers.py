from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from ecommerce_agent.config import _DEFAULT_CHAT_MODELS


def test_eval_prompt_is_the_gift_question():
    from evals.evaluate_llm_provider_latency import PROMPT

    assert PROMPT == "Hi, I want to buy a gift for my 2.5 year old nephew"


def test_chat_providers_cover_each_integrated_backend():
    from evals.evaluate_llm_provider_latency import CHAT_PROVIDERS

    assert CHAT_PROVIDERS == ("openai", "openrouter", "mistral", "ollama")


def test_usage_from_response_reads_token_counts():
    from evals.evaluate_llm_provider_latency import usage_from_response

    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=12,
            completion_tokens=34,
            total_tokens=46,
        )
    )

    assert usage_from_response(response) == {
        "prompt_tokens": 12,
        "completion_tokens": 34,
        "total_tokens": 46,
    }


def test_usage_from_response_handles_missing_usage():
    from evals.evaluate_llm_provider_latency import usage_from_response

    assert usage_from_response(SimpleNamespace(usage=None)) == {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }


def test_is_configured_requires_provider_api_key(monkeypatch):
    from evals import evaluate_llm_provider_latency as mod

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-test")

    assert mod.is_configured("openai") is False
    assert mod.is_configured("mistral") is True
    assert mod.is_configured("ollama") is True


def test_evaluate_provider_records_latency_and_tokens(monkeypatch):
    from evals import evaluate_llm_provider_latency as mod

    times = iter([1.0, 1.25])
    monkeypatch.setattr(mod.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(
        mod,
        "chat_client",
        lambda provider: SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(content="toy ideas")
                            )
                        ],
                        usage=SimpleNamespace(
                            prompt_tokens=10,
                            completion_tokens=20,
                            total_tokens=30,
                        ),
                    )
                )
            )
        ),
    )
    span = MagicMock()
    monkeypatch.setattr(
        mod.mlflow,
        "start_span",
        lambda **kwargs: MagicMock(
            __enter__=lambda self: span, __exit__=lambda *args: False
        ),
    )

    result = mod.evaluate_provider("mistral")

    assert result["provider"] == "mistral"
    assert result["model"] == _DEFAULT_CHAT_MODELS["mistral"]
    assert result["latency_ms"] == pytest.approx(250.0)
    assert result["prompt_tokens"] == 10
    assert result["completion_tokens"] == 20
    assert result["total_tokens"] == 30
    assert result["output"] == "toy ideas"
    span.set_inputs.assert_called_once()
    span.set_outputs.assert_called_once()


def test_run_eval_skips_unconfigured_providers_and_traces_the_rest(monkeypatch):
    from evals import evaluate_llm_provider_latency as mod

    monkeypatch.setattr(mod, "is_configured", lambda provider: provider == "mistral")
    monkeypatch.setattr(
        mod,
        "evaluate_provider",
        lambda provider: {
            "provider": provider,
            "model": "mistral-small",
            "latency_ms": 100.0,
            "prompt_tokens": 8,
            "completion_tokens": 16,
            "total_tokens": 24,
            "output": "ok",
        },
    )
    logged = []
    nested = MagicMock()
    nested.__enter__.return_value = nested
    nested.__exit__.return_value = False
    parent = MagicMock()
    parent.__enter__.return_value = parent
    parent.__exit__.return_value = False

    def fake_start_run(**kwargs):
        logged.append(kwargs)
        return nested if kwargs.get("nested") else parent

    monkeypatch.setattr(mod.mlflow, "set_tracking_uri", Mock())
    monkeypatch.setattr(mod.mlflow, "set_experiment", Mock())
    monkeypatch.setattr(mod, "openai_autolog", Mock())
    monkeypatch.setattr(mod.mlflow, "start_run", fake_start_run)
    monkeypatch.setattr(mod.mlflow, "log_param", Mock())
    monkeypatch.setattr(mod.mlflow, "log_metric", Mock())

    results = mod.run_eval(providers=("openai", "mistral"))

    skipped = next(row for row in results if row["provider"] == "openai")
    ran = next(row for row in results if row["provider"] == "mistral")
    assert skipped["skipped"] is True
    assert ran["latency_ms"] == 100.0
    assert ran["total_tokens"] == 24
    mod.mlflow.set_experiment.assert_called_once_with(mod.EXPERIMENT_NAME)
    mod.openai_autolog.assert_called_once()
    assert any(kwargs.get("nested") for kwargs in logged)
    mod.mlflow.log_metric.assert_any_call("latency_ms", 100.0)
    mod.mlflow.log_metric.assert_any_call("total_tokens", 24)
