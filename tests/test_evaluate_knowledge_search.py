from unittest.mock import Mock

import pytest

from ecommerce_agent.config import PROJECT_ROOT


def test_default_dataset_is_retrieval_eval_json():
    from evals.evaluate_knowledge_search import DEFAULT_DATASET

    assert DEFAULT_DATASET == PROJECT_ROOT / "evals" / "datasets" / "retrieval_eval_dataset.json"
    assert DEFAULT_DATASET.is_file()


def test_parse_args_requires_search_type():
    from evals.evaluate_knowledge_search import parse_args

    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_accepts_search_type():
    from evals.evaluate_knowledge_search import parse_args

    args = parse_args(["--search-type", "genai_001_embedding"])
    assert args.search_type == "genai_001_embedding"


def test_load_dataset_reads_synthetic_questions():
    from evals.evaluate_knowledge_search import load_dataset

    rows = load_dataset(PROJECT_ROOT / "evals" / "datasets" / "retrieval_eval_dataset.json")
    assert len(rows) >= 1
    first = rows[0]
    assert {"id", "content", "synthetic_question"} <= set(first)
    shipping = next(r for r in rows if r["id"] == 1)
    assert "How long does shipping take?" in shipping["content"]
    assert shipping["synthetic_question"]


def test_rank_of_expected_is_one_based_and_none_when_missing():
    from evals.evaluate_knowledge_search import rank_of_expected

    expected = "## How long does shipping take?\nStandard shipping takes 3–5 business days."
    results = [
        {"content": "## Do you ship internationally?\nNo, we only ship within Argentina."},
        {"content": expected},
    ]
    assert rank_of_expected(expected, results) == 2
    assert rank_of_expected(expected, [{"content": "unrelated"}]) is None


def test_rank_of_expected_matches_normalized_whitespace():
    from evals.evaluate_knowledge_search import rank_of_expected

    expected = "## How long does shipping take?\nStandard shipping takes 3–5 business days."
    results = [
        {
            "content": "  ## How long does shipping take? \n\n Standard shipping takes 3–5 business days.  "
        }
    ]
    assert rank_of_expected(expected, results) == 1


def test_summarize_computes_hit_at_k_and_mrr():
    from evals.evaluate_knowledge_search import summarize

    metrics = summarize([1, 2, None, 1], k=5)
    assert metrics["n"] == 4
    assert metrics["hit_at_1"] == 0.5
    assert metrics["hit_at_k"] == 0.75
    assert metrics["mrr"] == pytest.approx(0.625)


def test_parse_args_requires_search_type():
    from evals.evaluate_knowledge_search import parse_args

    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_accepts_search_type():
    from evals.evaluate_knowledge_search import parse_args

    args = parse_args(["--search-type", "genai_001_embedding"])
    assert args.search_type == "genai_001_embedding"


def test_evaluate_row_calls_search_knowledge(monkeypatch):
    from evals import evaluate_knowledge_search as mod

    search = Mock(
        return_value={
            "status": "success",
            "results": [
                {
                    "content": "## How long does shipping take?\nStandard shipping takes 3–5 business days."
                }
            ],
        }
    )
    monkeypatch.setattr(mod, "search_knowledge", search)
    times = iter([1.0, 1.25])
    monkeypatch.setattr(mod.time, "perf_counter", lambda: next(times))

    row = mod.evaluate_row(
        {
            "id": 1,
            "content": "## How long does shipping take?\nStandard shipping takes 3–5 business days.",
            "synthetic_question": "What's the usual time frame for delivery?",
        },
        top_k=5,
        document_id="doc-1",
    )

    search.assert_called_once_with(
        "What's the usual time frame for delivery?",
        document_id="doc-1",
        top_k=5,
    )
    assert row["rank"] == 1
    assert row["hit_at_1"] is True
    assert row["hit_at_k"] is True
    assert row["latency_ms"] == pytest.approx(250.0)


def test_run_eval_aggregates_mocked_search(monkeypatch, tmp_path):
    from evals import evaluate_knowledge_search as mod

    dataset_path = tmp_path / "retrieval.json"
    dataset_path.write_text(
        """
[
  {
    "id": 1,
    "content": "## gold A\\nanswer A",
    "synthetic_question": "ask A"
  },
  {
    "id": 2,
    "content": "## gold B\\nanswer B",
    "synthetic_question": "ask B"
  }
]
""".strip(),
        encoding="utf-8",
    )

    def fake_search(query, document_id=None, top_k=5):
        if query == "ask A":
            return {"status": "success", "results": [{"content": "## gold A\nanswer A"}]}
        return {"status": "success", "results": [{"content": "wrong"}]}

    monkeypatch.setattr(mod, "search_knowledge", fake_search)

    report = mod.run_eval(dataset_path, top_k=5)

    assert report["metrics"]["n"] == 2
    assert report["metrics"]["hit_at_1"] == 0.5
    assert report["metrics"]["hit_at_k"] == 0.5
    assert report["metrics"]["mrr"] == 0.5
    assert [row["rank"] for row in report["rows"]] == [1, None]
    assert "latency_ms" in report["metrics"]
    assert report["metrics"]["latency_ms"] >= 0
