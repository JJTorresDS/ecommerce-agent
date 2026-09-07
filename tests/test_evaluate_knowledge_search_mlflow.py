from contextlib import nullcontext

import pytest


def test_parse_args_requires_search_type_and_experiment():
    from evals.evaluate_knowledge_search_mlflow import parse_args

    with pytest.raises(SystemExit):
        parse_args([])
    with pytest.raises(SystemExit):
        parse_args(["--search-type", "genai_001_embedding"])
    with pytest.raises(SystemExit):
        parse_args(["--experiment", "ecommerce-agent-search_eval"])


def test_parse_args_accepts_search_type_and_experiment():
    from evals.evaluate_knowledge_search_mlflow import parse_args

    args = parse_args(
        [
            "--search-type",
            "genai_001_embedding",
            "--experiment",
            "ecommerce-agent-search_eval",
        ]
    )
    assert args.search_type == "genai_001_embedding"
    assert args.experiment == "ecommerce-agent-search_eval"


def test_ensure_experiment_creates_when_missing(monkeypatch):
    from evals import evaluate_knowledge_search_mlflow as mod

    created = []
    set_to = []
    monkeypatch.setattr(mod.mlflow, "get_experiment_by_name", lambda name: None)
    monkeypatch.setattr(
        mod.mlflow, "create_experiment", lambda name: created.append(name) or "exp-id"
    )
    monkeypatch.setattr(mod.mlflow, "set_experiment", lambda name: set_to.append(name))

    mod.ensure_experiment("ecommerce-agent-search_eval")

    assert created == ["ecommerce-agent-search_eval"]
    assert set_to == ["ecommerce-agent-search_eval"]


def test_ensure_experiment_reuses_existing(monkeypatch):
    from evals import evaluate_knowledge_search_mlflow as mod

    created = []
    set_to = []
    monkeypatch.setattr(mod.mlflow, "get_experiment_by_name", lambda name: object())
    monkeypatch.setattr(mod.mlflow, "create_experiment", lambda name: created.append(name))
    monkeypatch.setattr(mod.mlflow, "set_experiment", lambda name: set_to.append(name))

    mod.ensure_experiment("ecommerce-agent-search_eval")

    assert created == []
    assert set_to == ["ecommerce-agent-search_eval"]


def test_search_eval_identity_run_name():
    from evals.evaluate_knowledge_search_mlflow import SearchEvalIdentity

    identity = SearchEvalIdentity(
        search_type="genai_001_embedding",
        embedding_model="gemini-embedding-001",
    )
    assert identity.run_name == "search-eval-genai_001_embedding-gemini-embedding-001"


def test_log_to_mlflow_logs_search_type_and_latency(monkeypatch):
    from evals import evaluate_knowledge_search_mlflow as mod

    logged = {"params": {}, "metrics": {}, "run_name": None}
    monkeypatch.setattr(
        mod.mlflow,
        "start_run",
        lambda **kwargs: logged.__setitem__("run_name", kwargs.get("run_name"))
        or nullcontext(),
    )
    monkeypatch.setattr(
        mod.mlflow, "log_param", lambda key, value: logged["params"].__setitem__(key, value)
    )
    monkeypatch.setattr(
        mod.mlflow, "log_metric", lambda key, value: logged["metrics"].__setitem__(key, value)
    )
    monkeypatch.setattr(mod.mlflow, "log_table", lambda **kwargs: None)

    report = {
        "rows": [{"id": 1, "rank": 1, "hit_at_k": True, "latency_ms": 12.5}],
        "metrics": {
            "n": 1,
            "hit_at_1": 1.0,
            "hit_at_k": 1.0,
            "mrr": 1.0,
            "latency_ms": 12.5,
        },
    }
    identity = mod.SearchEvalIdentity(
        search_type="genai_001_embedding",
        embedding_model="gemini-embedding-001",
    )
    mod.log_to_mlflow(
        report,
        dataset_path=mod.DEFAULT_DATASET,
        top_k=5,
        document_id=None,
        identity=identity,
    )

    assert logged["run_name"] == "search-eval-genai_001_embedding-gemini-embedding-001"
    assert logged["params"]["search_type"] == "genai_001_embedding"
    assert logged["params"]["embedding_model"] == "gemini-embedding-001"
    assert logged["metrics"]["latency_ms"] == 12.5


def test_table_from_rows_is_column_oriented():
    from evals.evaluate_knowledge_search_mlflow import table_from_rows

    table = table_from_rows(
        [
            {"id": 1, "rank": 1, "hit_at_k": True},
            {"id": 2, "rank": None, "hit_at_k": False},
        ]
    )
    assert table == {
        "id": [1, 2],
        "rank": [1, None],
        "hit_at_k": [True, False],
    }


def test_table_from_rows_empty():
    from evals.evaluate_knowledge_search_mlflow import table_from_rows

    assert table_from_rows([]) == {}
