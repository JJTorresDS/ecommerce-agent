import os
from types import SimpleNamespace

import pytest

from ecommerce_agent.config import PROJECT_ROOT, _DEFAULT_CHAT_MODELS


def test_default_dataset_is_llm_eval_json():
    from evals.evaluate_llm_response import DEFAULT_DATASET

    assert DEFAULT_DATASET == PROJECT_ROOT / "evals" / "datasets" / "llm_eval_dataset.json"
    assert DEFAULT_DATASET.is_file()


def test_parse_args_requires_provider_and_experiment():
    from evals.evaluate_llm_response import parse_args

    with pytest.raises(SystemExit):
        parse_args([])
    with pytest.raises(SystemExit):
        parse_args(["--provider", "mistral"])
    with pytest.raises(SystemExit):
        parse_args(["--experiment", "ecommerce-agent-llm_eval"])


def test_parse_args_accepts_provider_experiment_and_has_no_model_flag():
    from evals.evaluate_llm_response import parse_args

    args = parse_args(
        ["--provider", "mistral", "--experiment", "ecommerce-agent-llm_eval"]
    )
    assert args.provider == "mistral"
    assert args.experiment == "ecommerce-agent-llm_eval"
    assert args.n is None
    assert not hasattr(args, "model")


def test_parse_args_accepts_optional_n():
    from evals.evaluate_llm_response import parse_args

    args = parse_args(
        [
            "--provider",
            "mistral",
            "--experiment",
            "ecommerce-agent-llm_eval",
            "--n",
            "3",
        ]
    )
    assert args.n == 3


def test_limit_eval_dataset_keeps_all_when_n_is_none():
    from evals.evaluate_llm_response import limit_eval_dataset

    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert limit_eval_dataset(rows, None) == rows


def test_limit_eval_dataset_takes_first_n():
    from evals.evaluate_llm_response import limit_eval_dataset

    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    assert limit_eval_dataset(rows, 2) == [{"id": 1}, {"id": 2}]


def test_ensure_experiment_creates_when_missing(monkeypatch):
    from evals import evaluate_llm_response as mod

    created = []
    set_to = []
    monkeypatch.setattr(mod.mlflow, "get_experiment_by_name", lambda name: None)
    monkeypatch.setattr(
        mod.mlflow, "create_experiment", lambda name: created.append(name) or "exp-id"
    )
    monkeypatch.setattr(mod.mlflow, "set_experiment", lambda name: set_to.append(name))

    mod.ensure_experiment("ecommerce-agent-llm_eval")

    assert created == ["ecommerce-agent-llm_eval"]
    assert set_to == ["ecommerce-agent-llm_eval"]


def test_ensure_experiment_reuses_existing(monkeypatch):
    from evals import evaluate_llm_response as mod

    created = []
    set_to = []
    monkeypatch.setattr(mod.mlflow, "get_experiment_by_name", lambda name: object())
    monkeypatch.setattr(mod.mlflow, "create_experiment", lambda name: created.append(name))
    monkeypatch.setattr(mod.mlflow, "set_experiment", lambda name: set_to.append(name))

    mod.ensure_experiment("ecommerce-agent-llm_eval")

    assert created == []
    assert set_to == ["ecommerce-agent-llm_eval"]


def test_resolve_model_uses_provider_default():
    from evals.evaluate_llm_response import resolve_model

    assert resolve_model("openai") == _DEFAULT_CHAT_MODELS["openai"]
    assert resolve_model("mistral") == _DEFAULT_CHAT_MODELS["mistral"]


def test_provider_and_model_from_agent_reads_model_object():
    from evals.evaluate_llm_response import provider_and_model_from_agent

    agent = SimpleNamespace(
        model=SimpleNamespace(
            model="mistral-small",
            _client=SimpleNamespace(base_url="https://api.mistral.ai/v1"),
        )
    )
    identity = provider_and_model_from_agent(agent)
    assert identity.provider == "mistral"
    assert identity.model == "mistral-small"
    assert identity.run_name == "llm-eval-mistral-mistral-small"


def test_provider_and_model_from_agent_falls_back_to_cli_provider():
    from evals.evaluate_llm_response import provider_and_model_from_agent

    agent = SimpleNamespace(model=SimpleNamespace(model="gpt-4o-mini"))
    identity = provider_and_model_from_agent(agent, fallback_provider="openai")
    assert identity.provider == "openai"
    assert identity.model == "gpt-4o-mini"
    assert identity.run_name == "llm-eval-openai-gpt-4o-mini"


def test_build_eval_agent_points_build_model_at_requested_provider(monkeypatch):
    from evals import evaluate_llm_response as mod

    seen = {}
    monkeypatch.setattr(
        mod,
        "build_agent",
        lambda: SimpleNamespace(
            name="ecommerce_agent",
            instructions="x",
            hooks=None,
            tools=[],
        ),
    )

    def fake_build_model():
        seen["provider"] = mod.llm_mod.settings.llm_provider
        seen["model"] = mod.llm_mod.settings.model
        seen["api_key"] = mod.llm_mod.settings.api_key
        return SimpleNamespace(
            model=mod.llm_mod.settings.model,
            _client=SimpleNamespace(base_url="https://api.mistral.ai/v1"),
        )

    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-live")
    monkeypatch.setattr(mod.llm_mod, "build_model", fake_build_model)
    monkeypatch.setattr(mod, "Agent", lambda **kwargs: SimpleNamespace(**kwargs))

    agent = mod.build_eval_agent("mistral")

    assert seen["provider"] == "mistral"
    assert seen["model"] == _DEFAULT_CHAT_MODELS["mistral"]
    assert seen["api_key"] == "mistral-live"
    assert agent.model.model == _DEFAULT_CHAT_MODELS["mistral"]


def test_make_predict_fn_runs_agent_and_records_latency_and_tokens(monkeypatch):
    from evals import evaluate_llm_response as mod

    agent = SimpleNamespace(name="eval-agent")
    usage = SimpleNamespace(input_tokens=11, output_tokens=4, total_tokens=15)
    monkeypatch.setattr(
        mod.Runner,
        "run_sync",
        lambda _agent, question: SimpleNamespace(
            final_output="3–5 business days",
            context_wrapper=SimpleNamespace(usage=usage),
        ),
    )
    times = iter([1.0, 1.4])
    monkeypatch.setattr(mod.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(mod.time, "sleep", lambda seconds: None)

    stats = mod.new_run_stats()
    predict = mod.make_predict_fn(agent, stats)

    assert predict("How long does shipping take?") == "3–5 business days"
    assert stats["latency_ms"] == [pytest.approx(400.0)]
    assert stats["input_tokens"] == 11
    assert stats["output_tokens"] == 4
    assert stats["total_tokens"] == 15


def test_llm_eval_runs_sequentially_with_one_second_pause():
    from evals.evaluate_llm_response import MAX_WORKERS, PAUSE_SECONDS

    assert PAUSE_SECONDS == 1
    assert MAX_WORKERS == 1
    assert os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] == "1"


def test_predict_fn_waits_one_second_between_calls(monkeypatch):
    from evals import evaluate_llm_response as mod

    monkeypatch.setattr(
        mod.Runner,
        "run_sync",
        lambda agent, question: SimpleNamespace(
            final_output="ok",
            context_wrapper=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=0, output_tokens=0, total_tokens=0)
            ),
        ),
    )
    slept = []
    monkeypatch.setattr(mod.time, "sleep", lambda seconds: slept.append(seconds))

    predict = mod.make_predict_fn(SimpleNamespace(), mod.new_run_stats())
    predict("How long does shipping take?")

    assert slept == [1]


def test_log_run_attributes_logs_provider_model_latency_and_tokens(monkeypatch):
    from evals import evaluate_llm_response as mod

    logged = {"params": {}, "metrics": {}}
    monkeypatch.setattr(
        mod.mlflow, "log_param", lambda key, value: logged["params"].__setitem__(key, value)
    )
    monkeypatch.setattr(
        mod.mlflow, "log_metric", lambda key, value: logged["metrics"].__setitem__(key, value)
    )

    stats = {
        "latency_ms": [100.0, 300.0],
        "input_tokens": 20,
        "output_tokens": 8,
        "total_tokens": 28,
    }
    mod.log_run_attributes(
        provider="mistral", model="mistral-small", stats=stats, n=2
    )

    assert logged["params"]["provider"] == "mistral"
    assert logged["params"]["model"] == "mistral-small"
    assert logged["params"]["n"] == 2
    assert logged["metrics"]["latency_ms"] == 200.0
    assert logged["metrics"]["input_tokens"] == 20
    assert logged["metrics"]["output_tokens"] == 8
    assert logged["metrics"]["total_tokens"] == 28


def test_load_eval_dataset_reads_inputs_and_expectations():
    from evals.evaluate_llm_response import load_eval_dataset

    rows = load_eval_dataset(
        PROJECT_ROOT / "evals" / "datasets" / "llm_eval_dataset.json"
    )
    assert len(rows) >= 1
    assert "question" in rows[0]["inputs"]
    assert "expected_response" in rows[0]["expectations"]
